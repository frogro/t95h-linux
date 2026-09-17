include $(TOPDIR)/rules.mk
include $(INCLUDE_DIR)/kernel.mk
PKG_NAME:=t95h-media
PKG_RELEASE:=2
PKG_LICENSE:=GPL-2.0-only
include $(INCLUDE_DIR)/package.mk

define KernelPackage/t95h-media
  SUBMENU:=Video Support
  TITLE:=T95H HDMI, audio and Cedrus backport
  DEPENDS:=@TARGET_sunxi @DISPLAY_SUPPORT +kmod-drm-dma-helper +kmod-drm-display-helper +kmod-sound-core +kmod-sound-soc-core +kmod-video-core +kmod-video-mem2mem +kmod-video-dma-contig +kmod-regmap-mmio
  KCONFIG:= \
 CONFIG_DRM_SUN4I CONFIG_DRM_SUN8I_MIXER CONFIG_DRM_SUN8I_DW_HDMI \
 CONFIG_DRM_SUN8I_TCON_TOP CONFIG_DRM_DW_HDMI CONFIG_DRM_DW_HDMI_I2S_AUDIO \
 CONFIG_DRM_PANEL=y CONFIG_DRM_SUN4I_BACKEND=n CONFIG_DRM_SUN4I_HDMI=n \
 CONFIG_DRM_SUN6I_DSI=n CONFIG_MEDIA_CEC_SUPPORT=y CONFIG_CEC_CORE CONFIG_DRM_DW_HDMI_CEC \
 CONFIG_SUN8I_DE2_CCU=y CONFIG_SUN50I_IOMMU=y \
 CONFIG_SND_SUN4I_CODEC CONFIG_SND_SOC_SUNXI_AHUB \
 CONFIG_SND_SOC_SUNXI_AHUB_DAM CONFIG_SND_SOC_SUNXI_MACH \
 CONFIG_SND_SOC_HDMI_CODEC CONFIG_SND_SOC_SUNXI_AAUDIO=n \
 CONFIG_SND_SOC_SUNXI_DEBUG=n CONFIG_STAGING=y CONFIG_STAGING_MEDIA=y \
 CONFIG_VIDEO_SUNXI=y CONFIG_VIDEO_SUNXI_CEDRUS CONFIG_MEDIA_PLATFORM_DRIVERS=y CONFIG_V4L_MEM2MEM_DRIVERS=y CONFIG_VIDEO_SUN50I_DI300
  FILES:= \
 $(LINUX_DIR)/drivers/media/platform/sunxi/sun50i-di300/sun50i-di300.ko \
 $(LINUX_DIR)/drivers/media/cec/core/cec.ko \
 $(LINUX_DIR)/drivers/gpu/drm/sun4i/sun4i-drm.ko \
 $(LINUX_DIR)/drivers/gpu/drm/sun4i/sun4i-tcon.ko \
 $(LINUX_DIR)/drivers/gpu/drm/sun4i/sun4i_tv.ko \
 $(LINUX_DIR)/drivers/gpu/drm/sun4i/sun6i_drc.ko \
 $(LINUX_DIR)/drivers/gpu/drm/sun4i/sun8i-mixer.ko \
 $(LINUX_DIR)/drivers/gpu/drm/sun4i/sun8i-drm-hdmi.ko \
 $(LINUX_DIR)/drivers/gpu/drm/sun4i/sun8i_tcon_top.ko \
 $(LINUX_DIR)/drivers/gpu/drm/bridge/synopsys/dw-hdmi.ko \
 $(LINUX_DIR)/drivers/gpu/drm/bridge/synopsys/dw-hdmi-i2s-audio.ko \
 $(LINUX_DIR)/drivers/gpu/drm/bridge/synopsys/dw-hdmi-cec.ko \
 $(LINUX_DIR)/sound/soc/codecs/snd-soc-hdmi-codec.ko \
 $(LINUX_DIR)/sound/soc/sunxi/sun4i-codec.ko \
 $(LINUX_DIR)/sound/soc/sunxi_v2/snd_soc_sunxi_ahub.ko \
 $(LINUX_DIR)/sound/soc/sunxi_v2/snd_soc_sunxi_ahub_dam.ko \
 $(LINUX_DIR)/sound/soc/sunxi_v2/snd_soc_sunxi_machine.ko \
 $(LINUX_DIR)/drivers/staging/media/sunxi/cedrus/sunxi-cedrus.ko
  AUTOLOAD:=$(call AutoProbe,snd-soc-hdmi-codec dw-hdmi-i2s-audio dw-hdmi-cec sun4i-drm sun4i-tcon sun8i-mixer sun8i-drm-hdmi sun8i_tcon_top sun4i-codec snd_soc_sunxi_ahub snd_soc_sunxi_ahub_dam snd_soc_sunxi_machine sunxi-cedrus sun50i-di300)
endef

define Build/Compile
endef
$(eval $(call KernelPackage,t95h-media))
