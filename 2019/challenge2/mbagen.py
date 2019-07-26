import os
import sys
import random
import gmpy2
import tempfile
import shutil
import zipfile
import json

handlers = []
values = [random.randint(0, 1 << 58 - 1) for i in range(8)]


def reg(name):
    handlers.append(f)
    return f


def egcd(a, b):
    if a == 0:
        return (b, 0, 1)
    else:
        g, y, x = egcd(b % a, a)
        return (g, x - (b // a) * y, y)


def modinv(a, m):
    g, x, y = egcd(a, m)
    if g != 1:
        raise Exception('modular inverse does not exist')
    else:
        return x % m


handlers += [
    lambda: 'a = a * %duLL;' % (random.randint(0, 1 << 58) * 2 + 1),
    lambda: 'a = a + %duLL;' % (random.randint(0, 1 << 58)),
    lambda: 'a = a - %duLL;' % (random.randint(0, 1 << 58)),
    lambda: 'a = a ^ %duLL;' % (random.randint(0, 1 << 58)),
]

res = []
for i in range(200):
    expr = ''.join(random.choice(handlers)() for i in range(8))
    res.append(expr)

    exec """
def func%d(a):
	%s
	return a
""".strip() % (i, expr.replace('uLL', '').replace(';', '&0xffffffffffffffff;'))


def invert(expr):
    if '*' in expr:
        expr = 'a = a * modinv(%s, 2 ** 64)' % expr.split('*')[
            1].replace('uLL', '')
    elif '+' in expr:
        expr = expr.replace('+', '-')
    elif '-' in expr:
        expr = expr.replace('-', '+')
    return expr+'&0xFFFFFFFFFFFFFFFF'


inv = [';'.join([invert(x) for x in item.strip(
    ';').split(';')[::-1]])+';' for item in res]
res = ['void func%d() {%s table[next_ptr()]();}' % (i, expr)
       for i, expr in enumerate(res)]
for i, expr in enumerate(inv):
    exec """
def invfunc%d(a):
	%s
	return a
""".strip() % (i, expr.replace('uLL', ''))
funcs = [eval('func%d' % i) for i in range(200)]
invfuncs = [eval('invfunc%d' % i) for i in range(200)]


def generate(output_fd):
    print >> output_fd, """
	#include <stdint.h>
	#include <stdio.h>
	uint64_t a;
	uint64_t r;
	extern void (*table[%d + 1])();
	void nop() {}
	uint64_t next_ptr() {
		r = r * 7 / 8;
		if(!r) {
			return sizeof(table) / sizeof(table[0]) - 1;
		}
		return r % (sizeof(table) / sizeof(table[0]) - 1);
	}
	""".replace('%d', str(len(res)))
    print >> output_fd, '\n'.join(res)
    print >> output_fd, 'void (*table[])() = {%s, nop};' % ','.join(
        'func%d' % i for i, _ in enumerate(res))

    keys = []
    orig = values[:]

    for i in range(8):
        r = random.randint(2 ** 32, 2**58 - 1)
        keys.append(r)
        value = values[i]
        while True:
            r = r * 7 / 8
            idx = r % len(res)
            if not r:
                break
            value = funcs[idx](value)
            value &= 0xffffffffffffffff
        values[i] = value

    for i in range(8):
        r = keys[i]
        value = values[i]
        print >> sys.stderr, orig[i],
        indexes = []
        while True:
            r = r * 7 / 8
            idx = r % len(res)
            if not r:
                break
            indexes.append(idx)
        for idx in indexes[::-1]:
            value = invfuncs[idx](value)
            value &= 0xffffffffffffffff
        assert value == orig[i]

    print >> sys.stderr
    # sys.stdout=sys.stderr

    print >> output_fd, """
	uint64_t values[] = {%s};
	uint64_t keys[] = {%s};
	int offset;
	int check(uint64_t input) {
		a = input;
		table[next_ptr()]();
		return a == values[offset];
	}

	#define WASM_EXPORT __attribute__((visibility("default")))

	WASM_EXPORT
	int main() {
		uint64_t input;
		char valid = 1;
		setvbuf(stdin, 0, 2, 0);
		setvbuf(stdout, 0, 2, 0);
		for(offset = 0; offset < 8; offset++) {
			r = keys[offset];
			if(scanf(" %%lld", &input) != 1) {
				valid = 0;
			}
			if(!check(input)) valid = 0;
		}
		puts(valid ? "correct!" : ":(");
		return !valid;
	}
	""" % (','.join(map(lambda x: '%suLL' % x, values)), ','.join(map(lambda x: '%suLL' % x, keys)))
    print >> sys.stderr, "Done, check out.c! The solution is above."
    return orig


def generate_wasm():
    dir = tempfile.mkdtemp()
    with open(dir + '/chal.c', 'wb') as fd:
        solution = generate(fd)
        fd.close()

    base = dir + '/chal'

    assert not os.system('emcc %s -o %s.js -O3' % (fd.name, base))
    z = zipfile.ZipFile(dir+'.zip', mode='w')
    z.write(base+'.js', 'chal.js')
    z.write(base+'.wasm', 'chal.wasm')
    z.close()

    with open(dir + '.solution', 'wb') as fd:
        fd.write(','.join(map(str, solution)))

    shutil.rmtree(dir)

    return dir + '.zip'


if __name__ == '__main__':
    print generate_wasm()
