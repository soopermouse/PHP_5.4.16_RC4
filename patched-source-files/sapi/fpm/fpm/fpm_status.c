
	/* $Id$ */
	/* (c) 2009 Jerome Loyet */

#include "php.h"
#include "SAPI.h"
#include <stdio.h>

#include "fpm_config.h"
#include "fpm_scoreboard.h"
#include "fpm_status.h"
#include "fpm_clock.h"
#include "fpm_scoreboard.h"
#include "zlog.h"
#include "fpm_atomic.h"
#include "fpm_conf.h"
#include "fpm_php.h"
#include <ext/standard/html.h>

static char *fpm_status_uri = NULL;
static char *fpm_status_ping_uri = NULL;
static char *fpm_status_ping_response = NULL;

/* Status values include untrusted FastCGI request metadata. Escape every dynamic
 * value for its output format, not only the query string. PHP 5.4 interface. */
#define FPM_RC6_TEXT 0
#define FPM_RC6_HTML 1
#define FPM_RC6_XML  2
#define FPM_RC6_JSON 3

static char *fpm_rc6_status_escape(const char *value, int fmt TSRMLS_DC)
{
    size_t len, out_len, i, o;
    char *out;
    const unsigned char *src;

    if (!value) {
        value = "";
    }
    len = strlen(value);
    if (fmt == FPM_RC6_HTML || fmt == FPM_RC6_XML) {
        int flags = ENT_QUOTES | ENT_SUBSTITUTE | ENT_DISALLOWED;
        flags |= (fmt == FPM_RC6_XML ? ENT_XML1 : ENT_HTML401);
        return php_escape_html_entities_ex((unsigned char *)value, len,
            &out_len, 0, flags, "UTF-8", 1 TSRMLS_CC);
    }
    if (fmt != FPM_RC6_JSON) {
        return estrdup(value);
    }
    /* Six bytes per input byte covers \\u00xx escapes and U+FFFD replacement.
     * Valid UTF-8 is kept as-is; invalid sequences are replaced with U+FFFD,
     * preventing invalid JSON output or injection via malformed bytes. */
    out = (char *)safe_emalloc(len, 6, 1);
    src = (const unsigned char *)value;
    o = 0;
    for (i = 0; i < len;) {
        unsigned char c = src[i];
        size_t n = 0, j;
        int valid = 1;
        if (c == '"' || c == '\\') {
            out[o++] = '\\';
            out[o++] = (char)c;
            i++;
        } else if (c <= 0x1f) {
            static const char hex[] = "0123456789abcdef";
            out[o++] = '\\'; out[o++] = 'u'; out[o++] = '0'; out[o++] = '0';
            out[o++] = hex[c >> 4]; out[o++] = hex[c & 15];
            i++;
        } else if (c < 0x80) {
            out[o++] = (char)c;
            i++;
        } else {
            if (c >= 0xc2 && c <= 0xdf) n = 2;
            else if (c >= 0xe0 && c <= 0xef) n = 3;
            else if (c >= 0xf0 && c <= 0xf4) n = 4;
            if (!n || i + n > len) valid = 0;
            if (valid) {
                for (j = 1; j < n; j++) {
                    if (src[i + j] < 0x80 || src[i + j] > 0xbf) {
                        valid = 0; break;
                    }
                }
                if (n == 3 && ((c == 0xe0 && src[i+1] < 0xa0) ||
                               (c == 0xed && src[i+1] >= 0xa0))) valid = 0;
                if (n == 4 && ((c == 0xf0 && src[i+1] < 0x90) ||
                               (c == 0xf4 && src[i+1] > 0x8f))) valid = 0;
            }
            if (valid) {
                memcpy(out + o, src + i, n);
                o += n;
                i += n;
            } else {
                memcpy(out + o, "\\uFFFD", 6);
                o += 6;
                i++;
            }
        }
    }
    out[o] = '\0';
    return out;
}


int fpm_status_init_child(struct fpm_worker_pool_s *wp) /* {{{ */
{
	if (!wp || !wp->config) {
		zlog(ZLOG_ERROR, "unable to init fpm_status because conf structure is NULL");
		return -1;
	}

	if (wp->config->pm_status_path) {
		fpm_status_uri = strdup(wp->config->pm_status_path);
	}

	if (wp->config->ping_path) {
		if (!wp->config->ping_response) {
			zlog(ZLOG_ERROR, "[pool %s] ping is set (%s) but ping.response is not set.", wp->config->name, wp->config->ping_path);
			return -1;
		}
		fpm_status_ping_uri = strdup(wp->config->ping_path);
		fpm_status_ping_response = strdup(wp->config->ping_response);
	}

	return 0;
}
/* }}} */

int fpm_status_handle_request(TSRMLS_D) /* {{{ */
{
	struct fpm_scoreboard_s scoreboard, *scoreboard_p;
	struct fpm_scoreboard_proc_s proc;
	char *buffer, *time_format, time_buffer[64];
	time_t now_epoch;
	int full, format;
	char *short_syntax, *short_post;
	char *full_pre, *full_syntax, *full_post, *full_separator;

	if (!SG(request_info).request_uri) {
		return 0;
	}

	/* PING */
	if (fpm_status_ping_uri && fpm_status_ping_response && !strcmp(fpm_status_ping_uri, SG(request_info).request_uri)) {
		fpm_request_executing();
		sapi_add_header_ex(ZEND_STRL("Content-Type: text/plain"), 1, 1 TSRMLS_CC);
		sapi_add_header_ex(ZEND_STRL("Expires: Thu, 01 Jan 1970 00:00:00 GMT"), 1, 1 TSRMLS_CC);
		sapi_add_header_ex(ZEND_STRL("Cache-Control: no-cache, no-store, must-revalidate, max-age=0"), 1, 1 TSRMLS_CC);
		SG(sapi_headers).http_response_code = 200;

		/* handle HEAD */
		if (SG(request_info).headers_only) {
			return 1;
		}

		PUTS(fpm_status_ping_response);
		return 1;
	}

	/* STATUS */
	if (fpm_status_uri && !strcmp(fpm_status_uri, SG(request_info).request_uri)) {
		fpm_request_executing();

		scoreboard_p = fpm_scoreboard_get();
		if (!scoreboard_p) {
			zlog(ZLOG_ERROR, "status: unable to find or access status shared memory");
			SG(sapi_headers).http_response_code = 500;
			sapi_add_header_ex(ZEND_STRL("Content-Type: text/plain"), 1, 1 TSRMLS_CC);
			sapi_add_header_ex(ZEND_STRL("Expires: Thu, 01 Jan 1970 00:00:00 GMT"), 1, 1 TSRMLS_CC);
			sapi_add_header_ex(ZEND_STRL("Cache-Control: no-cache, no-store, must-revalidate, max-age=0"), 1, 1 TSRMLS_CC);
			PUTS("Internal error. Please review log file for errors.");
			return 1;
		}

		if (!fpm_spinlock(&scoreboard_p->lock, 1)) {
			zlog(ZLOG_NOTICE, "[pool %s] status: scoreboard already in used.", scoreboard_p->pool);
			SG(sapi_headers).http_response_code = 503;
			sapi_add_header_ex(ZEND_STRL("Content-Type: text/plain"), 1, 1 TSRMLS_CC);
			sapi_add_header_ex(ZEND_STRL("Expires: Thu, 01 Jan 1970 00:00:00 GMT"), 1, 1 TSRMLS_CC);
			sapi_add_header_ex(ZEND_STRL("Cache-Control: no-cache, no-store, must-revalidate, max-age=0"), 1, 1 TSRMLS_CC);
			PUTS("Server busy. Please try again later.");
			return 1;
		}
		/* copy the scoreboard not to bother other processes */
		scoreboard = *scoreboard_p;
		fpm_unlock(scoreboard_p->lock);

		if (scoreboard.idle < 0 || scoreboard.active < 0) {
			zlog(ZLOG_ERROR, "[pool %s] invalid status values", scoreboard.pool);
			SG(sapi_headers).http_response_code = 500;
			sapi_add_header_ex(ZEND_STRL("Content-Type: text/plain"), 1, 1 TSRMLS_CC);
			sapi_add_header_ex(ZEND_STRL("Expires: Thu, 01 Jan 1970 00:00:00 GMT"), 1, 1 TSRMLS_CC);
			sapi_add_header_ex(ZEND_STRL("Cache-Control: no-cache, no-store, must-revalidate, max-age=0"), 1, 1 TSRMLS_CC);
			PUTS("Internal error. Please review log file for errors.");
			return 1;
		}

		/* send common headers */
		sapi_add_header_ex(ZEND_STRL("Expires: Thu, 01 Jan 1970 00:00:00 GMT"), 1, 1 TSRMLS_CC);
		sapi_add_header_ex(ZEND_STRL("Cache-Control: no-cache, no-store, must-revalidate, max-age=0"), 1, 1 TSRMLS_CC);
		SG(sapi_headers).http_response_code = 200;

		/* handle HEAD */
		if (SG(request_info).headers_only) {
			return 1;
		}

		/* full status ? */
		full = (fpm_php_get_string_from_table("_GET", "full" TSRMLS_CC) != NULL);
		short_syntax = short_post = NULL;
		full_separator = full_pre = full_syntax = full_post = NULL;
		format = FPM_RC6_TEXT;

		/* HTML */
		if (fpm_php_get_string_from_table("_GET", "html" TSRMLS_CC)) {
			sapi_add_header_ex(ZEND_STRL("Content-Type: text/html"), 1, 1 TSRMLS_CC);
			time_format = "%d/%b/%Y:%H:%M:%S %z";
			format = FPM_RC6_HTML;

			short_syntax =
				"<!DOCTYPE html PUBLIC \"-//W3C//DTD XHTML 1.0 Strict//EN\" \"http://www.w3.org/TR/xhtml1/DTD/xhtml1-strict.dtd\">\n"
				"<html xmlns=\"http://www.w3.org/1999/xhtml\" xml:lang=\"en\" lang=\"en\">\n"
				"<head><title>PHP-FPM Status Page</title></head>\n"
				"<body>\n"
				"<table>\n"
					"<tr><th>pool</th><td>%s</td></tr>\n"
					"<tr><th>process manager</th><td>%s</td></tr>\n"
					"<tr><th>start time</th><td>%s</td></tr>\n"
					"<tr><th>start since</th><td>%lu</td></tr>\n"
					"<tr><th>accepted conn</th><td>%lu</td></tr>\n"
#ifdef HAVE_FPM_LQ
					"<tr><th>listen queue</th><td>%u</td></tr>\n"
					"<tr><th>max listen queue</th><td>%u</td></tr>\n"
					"<tr><th>listen queue len</th><td>%d</td></tr>\n"
#endif
					"<tr><th>idle processes</th><td>%d</td></tr>\n"
					"<tr><th>active processes</th><td>%d</td></tr>\n"
					"<tr><th>total processes</th><td>%d</td></tr>\n"
					"<tr><th>max active processes</th><td>%d</td></tr>\n"
					"<tr><th>max children reached</th><td>%u</td></tr>\n"
					"<tr><th>slow requests</th><td>%lu</td></tr>\n"
				"</table>\n";

			if (!full) {
				short_post = "</body></html>";
			} else {
				full_pre =
					"<table border=\"1\">\n"
					"<tr>"
						"<th>pid</th>"
						"<th>state</th>"
						"<th>start time</th>"
						"<th>start since</th>"
						"<th>requests</th>"
						"<th>request duration</th>"
						"<th>request method</th>"
						"<th>request uri</th>"
						"<th>content length</th>"
						"<th>user</th>"
						"<th>script</th>"
#ifdef HAVE_FPM_LQ
						"<th>last request cpu</th>"
#endif
						"<th>last request memory</th>"
					"</tr>\n";

				full_syntax =
					"<tr>"
						"<td>%d</td>"
						"<td>%s</td>"
						"<td>%s</td>"
						"<td>%lu</td>"
						"<td>%lu</td>"
						"<td>%lu</td>"
						"<td>%s</td>"
						"<td>%s%s%s</td>"
						"<td>%zu</td>"
						"<td>%s</td>"
						"<td>%s</td>"
#ifdef HAVE_FPM_LQ
						"<td>%.2f</td>"
#endif
						"<td>%zu</td>"
					"</tr>\n";

				full_post = "</table></body></html>";
			}

		/* XML */
		} else if (fpm_php_get_string_from_table("_GET", "xml" TSRMLS_CC)) {
			sapi_add_header_ex(ZEND_STRL("Content-Type: text/xml"), 1, 1 TSRMLS_CC);
			time_format = "%s";
			format = FPM_RC6_XML;

			short_syntax =
				"<?xml version=\"1.0\" ?>\n"
				"<status>\n"
				"<pool>%s</pool>\n"
				"<process-manager>%s</process-manager>\n"
				"<start-time>%s</start-time>\n"
				"<start-since>%lu</start-since>\n"
				"<accepted-conn>%lu</accepted-conn>\n"
#ifdef HAVE_FPM_LQ
				"<listen-queue>%u</listen-queue>\n"
				"<max-listen-queue>%u</max-listen-queue>\n"
				"<listen-queue-len>%d</listen-queue-len>\n"
#endif
				"<idle-processes>%d</idle-processes>\n"
				"<active-processes>%d</active-processes>\n"
				"<total-processes>%d</total-processes>\n"
				"<max-active-processes>%d</max-active-processes>\n"
				"<max-children-reached>%u</max-children-reached>\n"
				"<slow-requests>%lu</slow-requests>\n";

				if (!full) {
					short_post = "</status>";
				} else {
					full_pre = "<processes>\n";
					full_syntax = 
						"<process>"
							"<pid>%d</pid>"
							"<state>%s</state>"
							"<start-time>%s</start-time>"
							"<start-since>%lu</start-since>"
							"<requests>%lu</requests>"
							"<request-duration>%lu</request-duration>"
							"<request-method>%s</request-method>"
							"<request-uri>%s%s%s</request-uri>"
							"<content-length>%zu</content-length>"
							"<user>%s</user>"
							"<script>%s</script>"
#ifdef HAVE_FPM_LQ
							"<last-request-cpu>%.2f</last-request-cpu>"
#endif
							"<last-request-memory>%zu</last-request-memory>"
						"</process>\n"
					;
					full_post = "</processes>\n</status>";
				}

			/* JSON */
		} else if (fpm_php_get_string_from_table("_GET", "json" TSRMLS_CC)) {
			sapi_add_header_ex(ZEND_STRL("Content-Type: application/json"), 1, 1 TSRMLS_CC);
            format = FPM_RC6_JSON;
			time_format = "%s";

			short_syntax =
				"{"
				"\"pool\":\"%s\","
				"\"process manager\":\"%s\","
				"\"start time\":%s,"
				"\"start since\":%lu,"
				"\"accepted conn\":%lu,"
#ifdef HAVE_FPM_LQ
				"\"listen queue\":%u,"
				"\"max listen queue\":%u,"
				"\"listen queue len\":%d,"
#endif
				"\"idle processes\":%d,"
				"\"active processes\":%d,"
				"\"total processes\":%d,"
				"\"max active processes\":%d,"
				"\"max children reached\":%u,"
				"\"slow requests\":%lu";

			if (!full) {
				short_post = "}";
			} else {
				full_separator = ",";
				full_pre = ", \"processes\":[";

				full_syntax = "{"
					"\"pid\":%d,"
					"\"state\":\"%s\","
					"\"start time\":%s,"
					"\"start since\":%lu,"
					"\"requests\":%lu,"
					"\"request duration\":%lu,"
					"\"request method\":\"%s\","
					"\"request uri\":\"%s%s%s\","
					"\"content length\":%zu,"
					"\"user\":\"%s\","
					"\"script\":\"%s\","
#ifdef HAVE_FPM_LQ
					"\"last request cpu\":%.2f,"
#endif
					"\"last request memory\":%zu"
					"}";

				full_post = "]}";
			}

		/* TEXT */
		} else {
			sapi_add_header_ex(ZEND_STRL("Content-Type: text/plain"), 1, 1 TSRMLS_CC);
			time_format = "%d/%b/%Y:%H:%M:%S %z";

			short_syntax =
				"pool:                 %s\n"
				"process manager:      %s\n"
				"start time:           %s\n"
				"start since:          %lu\n"
				"accepted conn:        %lu\n"
#ifdef HAVE_FPM_LQ
				"listen queue:         %u\n"
				"max listen queue:     %u\n"
				"listen queue len:     %d\n"
#endif
				"idle processes:       %d\n"
				"active processes:     %d\n"
				"total processes:      %d\n"
				"max active processes: %d\n"
				"max children reached: %u\n"
				"slow requests:        %lu\n";

				if (full) {
					full_syntax =
						"\n"
						"************************\n"
						"pid:                  %d\n"
						"state:                %s\n"
						"start time:           %s\n"
						"start since:          %lu\n"
						"requests:             %lu\n"
						"request duration:     %lu\n"
						"request method:       %s\n"
						"request URI:          %s%s%s\n"
						"content length:       %zu\n"
						"user:                 %s\n"
						"script:               %s\n"
#ifdef HAVE_FPM_LQ
						"last request cpu:     %.2f\n"
#endif
						"last request memory:  %zu\n";
				}
		}

		strftime(time_buffer, sizeof(time_buffer) - 1, time_format, localtime(&scoreboard.start_epoch));
		now_epoch = time(NULL);
        {
            char *pool_field = fpm_rc6_status_escape(scoreboard.pool, format TSRMLS_CC);
		spprintf(&buffer, 0, short_syntax,
				pool_field,
				PM2STR(scoreboard.pm),
				time_buffer,
				now_epoch - scoreboard.start_epoch,
				scoreboard.requests,
#ifdef HAVE_FPM_LQ
				scoreboard.lq,
				scoreboard.lq_max,
				scoreboard.lq_len,
#endif
				scoreboard.idle,
				scoreboard.active,
				scoreboard.idle + scoreboard.active,
				scoreboard.active_max,
				scoreboard.max_children_reached,
				scoreboard.slow_rq);

		PUTS(buffer);
		efree(buffer);
            efree(pool_field);
        }

		if (short_post) {
			PUTS(short_post);
		}

		/* no need to test the var 'full' */
		if (full_syntax) {
			int i, first;
            char *query_string;
            char *request_method, *request_uri, *auth_user, *script_filename;
			struct timeval duration, now;
#ifdef HAVE_FPM_LQ
			float cpu;
#endif

			fpm_clock_get(&now);

			if (full_pre) {
				PUTS(full_pre);
			}

			first = 1;
			for (i=0; i<scoreboard_p->nprocs; i++) {
				if (!scoreboard_p->procs[i] || !scoreboard_p->procs[i]->used) {
					continue;
				}
				proc = *scoreboard_p->procs[i];

				if (first) {
					first = 0;
				} else {
					if (full_separator) {
						PUTS(full_separator);
					}
				}

                request_method = fpm_rc6_status_escape(
                    proc.request_method[0] != '\0' ? proc.request_method : "-", format TSRMLS_CC);
                request_uri = fpm_rc6_status_escape(
                    proc.request_uri[0] != '\0' ? proc.request_uri : "-", format TSRMLS_CC);
                query_string = proc.query_string[0] != '\0' ?
                    fpm_rc6_status_escape(proc.query_string, format TSRMLS_CC) : NULL;
                auth_user = fpm_rc6_status_escape(
                    proc.auth_user[0] != '\0' ? proc.auth_user : "-", format TSRMLS_CC);
                script_filename = fpm_rc6_status_escape(
                    proc.script_filename[0] != '\0' ? proc.script_filename : "-", format TSRMLS_CC);

#ifdef HAVE_FPM_LQ
				/* prevent NaN */
				if (proc.cpu_duration.tv_sec == 0 && proc.cpu_duration.tv_usec == 0) {
					cpu = 0.;
				} else {
					cpu = (proc.last_request_cpu.tms_utime + proc.last_request_cpu.tms_stime + proc.last_request_cpu.tms_cutime + proc.last_request_cpu.tms_cstime) / fpm_scoreboard_get_tick() / (proc.cpu_duration.tv_sec + proc.cpu_duration.tv_usec / 1000000.) * 100.;
				}
#endif

				if (proc.request_stage == FPM_REQUEST_ACCEPTING) {
					duration = proc.duration;
				} else {
					timersub(&now, &proc.accepted, &duration);
				}
				strftime(time_buffer, sizeof(time_buffer) - 1, time_format, localtime(&proc.start_epoch));
				spprintf(&buffer, 0, full_syntax,
					proc.pid,
					fpm_request_get_stage_name(proc.request_stage),
					time_buffer,
					now_epoch - proc.start_epoch,
					proc.requests,
					duration.tv_sec * 1000000UL + duration.tv_usec,
                    request_method,
                    request_uri,
					query_string ? "?" : "",
					query_string ? query_string : "",
					proc.content_length,
                    auth_user,
                    script_filename,
#ifdef HAVE_FPM_LQ
					proc.request_stage == FPM_REQUEST_ACCEPTING ? cpu : 0.,
#endif
					proc.request_stage == FPM_REQUEST_ACCEPTING ? proc.memory : 0);
				PUTS(buffer);
				efree(buffer);

                efree(request_method);
                efree(request_uri);
                if (query_string) efree(query_string);
                efree(auth_user);
                efree(script_filename);
			}

			if (full_post) {
				PUTS(full_post);
			}
		}

		return 1;
	}

	return 0;
}
/* }}} */

