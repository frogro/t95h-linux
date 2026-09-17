include $(TOPDIR)/rules.mk
PKG_NAME:=t95h-board
PKG_RELEASE:=7
PKG_LICENSE:=GPL-2.0-only
include $(INCLUDE_DIR)/kernel.mk
include $(INCLUDE_DIR)/package.mk

define Package/t95h-board
  SECTION:=utils
  CATEGORY:=Utilities
  TITLE:=T95H native board initialization
  DEPENDS:=@TARGET_sunxi +alsa-utils +kmod-t95h-power +kmod-t95h-xradio +iw +wpad-basic-mbedtls +kmod-usb-hid +kmod-i2c-gpio +kmod-t95h-compute +kmod-t95h-media +kmod-t95h-ir +kmod-btusb +wireguard-tools +kmod-crypto-aead +kmod-crypto-manager +kmod-crypto-null +kmod-crypto-cmac +kmod-crypto-hmac +kmod-crypto-user +kmod-crypto-rng +kmod-crypto-sha3 +kmod-crypto-sha256 +kmod-crypto-sha512 +kmod-crypto-lib-chacha20poly1305 +kmod-crypto-lib-curve25519 +kmod-udptunnel4 +kmod-udptunnel6 +kmod-wireguard +kmod-tun +kmod-veth +kmod-nf-socket +kmod-nf-tproxy +kmod-nft-socket +kmod-nft-tproxy +kmod-nft-bridge +kmod-sched-core +kmod-sched-cake +kmod-ifb
endef

define Package/t95h-board/conffiles
/etc/config/wireless
/etc/t95h-audio.conf
endef

define Build/Prepare
	$(INSTALL_DIR) $(PKG_BUILD_DIR)
	$(CP) ./src/* $(PKG_BUILD_DIR)/
endef

define Build/Compile
	$(TARGET_CC) $(TARGET_CFLAGS) $(TARGET_CPPFLAGS) -Wall -Wextra -o $(PKG_BUILD_DIR)/t95h-fd655 $(PKG_BUILD_DIR)/t95h-fd655.c $(TARGET_LDFLAGS)
endef

define Package/t95h-board/install
	$(CP) ./files/. $(1)/
	$(INSTALL_DIR) $(1)/etc/apk/repositories.d
	printf '%s\n' 'https://github.com/frogro/t95h-linux/releases/download/native-kmods-$(LINUX_VERSION)-$(LINUX_VERMAGIC)-$(T95H_FEED_ID)/packages.adb' > $(1)/etc/apk/repositories.d/t95h-kmods.list
	$(INSTALL_BIN) $(PKG_BUILD_DIR)/t95h-fd655 $(1)/usr/sbin/t95h-fd655
	$(INSTALL_DIR) $(1)/usr/share/t95h
	$(CP) $(1)/etc/apk/repositories.d/t95h-kmods.list $(1)/usr/share/t95h/kmods.list

endef
$(eval $(call BuildPackage,t95h-board))
