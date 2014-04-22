DESTDIR=
PKGNAME=whc-switch

default:
	echo "Nothing to compile - nothing to do! :D"

install:
	install -D -m 644 whc-switch@.service "${DESTDIR}/usr/lib/systemd/system/whc-switch@.service"
	install -D -m 755 whc-switch.py "${DESTDIR}/usr/share/${PKGNAME}/whc-switch.py"
	install -D -m 644 whc-switch.conf "${DESTDIR}/etc/whc-switch.conf"
	
remove:
	rm -f "${DESTDIR}/etc/whc-switch.conf
	rm -f "${DESTDIR}/usr/lib/systemd/system/whc-switch@.service"
	rm -f "${DESTDIR}/usr/share/${PKGNAME}/whc-switch.py"
