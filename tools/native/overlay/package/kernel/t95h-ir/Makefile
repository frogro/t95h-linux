include $(TOPDIR)/rules.mk
include $(INCLUDE_DIR)/kernel.mk
PKG_NAME:=t95h-ir
PKG_RELEASE:=1
PKG_LICENSE:=GPL-2.0-only
include $(INCLUDE_DIR)/package.mk

define KernelPackage/t95h-ir
  SUBMENU:=Other modules
  TITLE:=T95H infrared receiver (native sunxi driver)
  DEPENDS:=@TARGET_sunxi +kmod-input-core +kmod-input-evdev
  KCONFIG:=CONFIG_RC_CORE CONFIG_RC_DEVICES=y CONFIG_RC_DECODERS=y CONFIG_IR_SUNXI CONFIG_IR_NEC_DECODER CONFIG_LIRC=y
  FILES:=$(LINUX_DIR)/drivers/media/rc/rc-core.ko $(LINUX_DIR)/drivers/media/rc/sunxi-cir.ko $(LINUX_DIR)/drivers/media/rc/ir-nec-decoder.ko
  AUTOLOAD:=$(call AutoProbe,rc-core ir-nec-decoder sunxi-cir)
endef

define Build/Compile
endef
$(eval $(call KernelPackage,t95h-ir))
