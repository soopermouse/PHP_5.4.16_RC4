#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <libxml/parser.h>
#include <libxml/tree.h>
static int is_blank(const xmlChar* str)
{
	while (*str != '\0') {
		if (*str != ' '  && *str != 0x9 && *str != 0xa && *str != 0xd) {
			return 0;
		}
		str++;
	}
	return 1;
}
static void cleanup_xml_node(xmlNodePtr node)
{
	xmlNodePtr trav;
	xmlNodePtr del = NULL;

	trav = node->children;
	while (trav != NULL) {
		if (del != NULL) {
			xmlUnlinkNode(del);
			xmlFreeNode(del);
			del = NULL;
		}
		if (trav->type == XML_TEXT_NODE) {
			if (is_blank(trav->content)) {
				del = trav;
			}
		} else if ((trav->type != XML_ELEMENT_NODE) &&
		           (trav->type != XML_CDATA_SECTION_NODE)) {
			del = trav;
		} else if (trav->children != NULL) {
			cleanup_xml_node(trav);
		}
		trav = trav->next;
	}
	if (del != NULL) {
		xmlUnlinkNode(del);
		xmlFreeNode(del);
	}
}
int main(void) {
 const char *xml="<!DOCTYPE root [<!ENTITY harmless 'hello'>]><root>&harmless;</root>";
 xmlDocPtr doc=xmlReadMemory(xml,(int)strlen(xml),"case.xml",NULL,XML_PARSE_NONET|XML_PARSE_NOENT);
 if (!doc) return 10;
 if (!xmlGetIntSubset(doc)) return 11;
 cleanup_xml_node((xmlNodePtr)doc);
 if (!xmlGetIntSubset(doc)) { xmlFreeDoc(doc); return 12; }
 xmlFreeDoc(doc);
 xmlCleanupParser();
 puts("DTD attached until document cleanup");
 return 0;
}
