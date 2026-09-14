include $(TOPDIR)/rules.mk

PKG_NAME:=t95h-xradio
PKG_RELEASE:=1
PKG_LICENSE:=GPL-2.0
PKG_LICENSE_FILES:=LICENSE
PKG_BUILD_PARALLEL:=1

include $(INCLUDE_DIR)/kernel.mk
include $(INCLUDE_DIR)/package.mk

STAMP_CONFIGURED_DEPENDS := $(STAGING_DIR)/usr/include/mac80211-backport/backport/autoconf.h

define KernelPackage/t95h-xradio
  SUBMENU:=Wireless Drivers
  TITLE:=T95H XR819 SDIO wireless driver
  DEPENDS:=@TARGET_sunxi +kmod-mac80211 +kmod-mmc +t95h-xradio-firmware +kmod-t95h-power
  FILES:=$(PKG_BUILD_DIR)/xradio_wlan.ko
  AUTOLOAD:=$(call AutoProbe,xradio_wlan)
endef

define Build/Prepare
	mkdir -p $(PKG_BUILD_DIR)
	$(CP) ./src/. $(PKG_BUILD_DIR)/
endef

NOSTDINC_FLAGS := \
	$(KERNEL_NOSTDINC_FLAGS) \
	-I$(PKG_BUILD_DIR) \
	-I$(STAGING_DIR)/usr/include/mac80211-backport \
	-I$(STAGING_DIR)/usr/include/mac80211-backport/uapi \
	-I$(STAGING_DIR)/usr/include/mac80211 \
	-I$(STAGING_DIR)/usr/include/mac80211/uapi \
	-include backport/backport.h \
	-DXRADIO_MAC80211_HAS_RADIO_IDX

define Build/Compile
	+$(KERNEL_MAKE) $(PKG_JOBS) M="$(PKG_BUILD_DIR)" \
		CONFIG_XRADIO=m NOSTDINC_FLAGS="$(NOSTDINC_FLAGS)" modules
endef

$(eval $(call KernelPackage,t95h-xradio))
