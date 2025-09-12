all	: urqmd.e

urqmd.e:
	$(MAKE) -C src
	cp -f src/urqmd.e ./
	$(MAKE) -C src distclean

clean:
	$(MAKE) -C src clean
	rm -f urqmd.e

distclean:
	$(MAKE) -C src distclean
	rm -f urqmd.e
