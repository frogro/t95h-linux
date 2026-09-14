include $(TOPDIR)/rules.mk
PKG_NAME:=t95h-power
PKG_RELEASE:=1
PKG_LICENSE:=GPL-2.0-only
include $(INCLUDE_DIR)/kernel.mk
include $(INCLUDE_DIR)/package.mk

define KernelPackage/t95h-power
  SUBMENU:=Other modules
  TITLE:=T95H guarded WLAN and CPU power supplies
  DEPENDS:=@TARGET_sunxi +kmod-i2c-core
  KCONFIG:=CONFIG_REGMAP_I2C=y
  FILES:=$(PKG_BUILD_DIR)/t95h_aldo2.ko
endef

define Build/Prepare
	mkdir -p $(PKG_BUILD_DIR)
	$(CP) ./src/. $(PKG_BUILD_DIR)/
endef

define Build/Compile
	+$(KERNEL_MAKE) M="$(PKG_BUILD_DIR)" modules
endef
$(eval $(call KernelPackage,t95h-power))
