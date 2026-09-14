include $(TOPDIR)/rules.mk
PKG_NAME:=t95h-xradio-firmware
PKG_RELEASE:=1
include $(INCLUDE_DIR)/package.mk

define Package/t95h-xradio-firmware
  SECTION:=firmware
  CATEGORY:=Firmware
  TITLE:=Tested T95H XR819 firmware
endef

define Build/Compile
endef

define Package/t95h-xradio-firmware/install
	$(INSTALL_DIR) $(1)/lib/firmware/xr819
	$(INSTALL_DATA) ./files/*.bin $(1)/lib/firmware/xr819/
endef
$(eval $(call BuildPackage,t95h-xradio-firmware))
