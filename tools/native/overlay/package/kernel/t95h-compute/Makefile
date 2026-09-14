include $(TOPDIR)/rules.mk
PKG_NAME:=t95h-compute
PKG_RELEASE:=1
PKG_LICENSE:=GPL-2.0-only
include $(INCLUDE_DIR)/kernel.mk
include $(INCLUDE_DIR)/package.mk

define KernelPackage/t95h-compute
  SUBMENU:=Video Support
  TITLE:=T95H guarded GPU power and native Panfrost/CPU DVFS
  DEPENDS:=@TARGET_sunxi @DISPLAY_SUPPORT +kmod-t95h-power +kmod-drm-shmem-helper +kmod-drm-sched
  KCONFIG:=CONFIG_DRM_PANFROST CONFIG_ARM_ALLWINNER_SUN50I_CPUFREQ_NVMEM CONFIG_PM_GENERIC_DOMAINS=y CONFIG_PM_GENERIC_DOMAINS_OF=y CONFIG_PM_DEVFREQ=y CONFIG_DEVFREQ_GOV_SIMPLE_ONDEMAND=y CONFIG_IOMMU_SUPPORT=y CONFIG_IOMMU_IO_PGTABLE_LPAE=y
  FILES:=$(PKG_BUILD_DIR)/t95h_ana_provider.ko $(LINUX_DIR)/drivers/gpu/drm/panfrost/panfrost.ko $(LINUX_DIR)/drivers/cpufreq/sun50i-cpufreq-nvmem.ko
endef
# Intentionally no AUTOLOAD: GPU stays active before CPU DVFS is registered.
define Build/Prepare
	$(INSTALL_DIR) $(PKG_BUILD_DIR)
	$(CP) ./src/. $(PKG_BUILD_DIR)/
endef

define Build/Compile
	+$(KERNEL_MAKE) M="$(PKG_BUILD_DIR)" modules
endef
$(eval $(call KernelPackage,t95h-compute))
