CC=gcc
PYTHON_INCLUDE=/usr/include/python2.7
PYTHON_LIBRARY=/usr/lib/python2.7

default: wumanber.so

wumanber.so: wumanber_impl.c
	$(CC) -shared -O2 -o wumanber.so wumanber_impl.c 

clean:
	rm wumanber.so


