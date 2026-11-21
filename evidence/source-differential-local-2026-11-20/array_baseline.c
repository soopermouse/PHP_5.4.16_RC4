#include <stdio.h>
#include <stdlib.h>
#define E_ERROR 1
#define soap_error0(a,b) abort()
static int calc_dimension_12(const char* str)
{
	int i = 0, flag = 0;
	while (*str != '\0' && (*str < '0' || *str > '9') && (*str != '*')) {
		str++;
	}
	if (*str == '*') {
		i++;
		str++;
	}
	while (*str != '\0') {
		if (*str >= '0' && *str <= '9') {
			if (flag == 0) {
	   		i++;
	   		flag = 1;
	   	}
	  } else if (*str == '*') {
			soap_error0(E_ERROR, "Encoding: '*' may only be first arraySize value in list");
		} else {
			flag = 0;
		}
		str++;
	}
	return i;
}
int main(void) {
 const char *a[]={""," ","not_a_dimension","2","2,3","*"};
 for (int i=0;i<6;i++) printf("%d\n",calc_dimension_12(a[i]));
 return 0;
}
