PKG_NAME="t95h-hardware"
PKG_VERSION="1"
PKG_LICENSE="GPL"
PKG_DEPENDS_TARGET="toolchain linux"
PKG_SECTION="tools"
PKG_LONGDESC="Experimental T95H locked hardware modules and systemd startup"
PKG_TOOLCHAIN="manual"
make_target() {
  cp -a ${PKG_DIR}/sources/. ${PKG_BUILD}/
  kernel_make -C $(get_build_dir linux) M=${PKG_BUILD} modules
}
makeinstall_target() {
  local firmware_dir="${INSTALL}/$(get_full_firmware_dir)"
  mkdir -p ${INSTALL}/usr/lib/t95h ${INSTALL}/usr/lib/systemd/system/multi-user.target.wants ${INSTALL}/usr/lib/systemd/system/kodi.service.d ${INSTALL}/usr/share/bootloader "${firmware_dir}"
  cp ${PKG_BUILD}/t95h_aldo2.ko ${PKG_BUILD}/t95h_ana_provider.ko ${INSTALL}/usr/lib/t95h/
  cp ${PKG_DIR}/t95h.dtb ${INSTALL}/usr/share/bootloader/
  cp -a ${PKG_DIR}/firmware/. "${firmware_dir}/"
  cp ${PKG_DIR}/start-hardware ${INSTALL}/usr/lib/t95h/
  chmod 755 ${INSTALL}/usr/lib/t95h/start-hardware
  cp ${PKG_DIR}/prepare-regulatory ${INSTALL}/usr/lib/t95h/
  chmod 755 ${INSTALL}/usr/lib/t95h/prepare-regulatory
  cp ${PKG_DIR}/system.d/*.service ${INSTALL}/usr/lib/systemd/system/
  ln -s ../t95h-hardware.service ${INSTALL}/usr/lib/systemd/system/multi-user.target.wants/t95h-hardware.service
  ln -s ../t95h-regulatory.service ${INSTALL}/usr/lib/systemd/system/multi-user.target.wants/t95h-regulatory.service
  cp ${PKG_DIR}/kodi.conf ${INSTALL}/usr/lib/systemd/system/kodi.service.d/t95h.conf
}
