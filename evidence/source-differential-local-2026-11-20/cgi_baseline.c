#include <stdio.h>
#include <stddef.h>
#include <stdint.h>
static void check(int pilen, int slen){
 char env_path_info[]="abcd";
 char *orig_path_info=NULL;
 (void)orig_path_info;
char *path_info = env_path_info ? env_path_info + pilen - slen : NULL;
 if(!path_info) puts("null");
 else printf("%ld\n",(long)((intptr_t)path_info-(intptr_t)env_path_info));
}
int main(void){check(1,3);check(3,3);check(4,2);return 0;}
