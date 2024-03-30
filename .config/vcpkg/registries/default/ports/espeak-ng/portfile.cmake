vcpkg_from_github(
  OUT_SOURCE_PATH SOURCE_PATH
  REPO espeak-ng/espeak-ng
  REF cb62d93fd7b61d8593b9ae432e6e2a78e3711a77
  SHA512 105cf53bd2f208af1cfca2e380b411c61c08225698b72b4d033b972d37067173bb3825c12c70b8f019b5f2ff0cce6c8e28faab8c54a92b3646f912e86af18bec
  HEAD_REF master
  PATCHES 01-install-targets.patch
)
vcpkg_cmake_configure(
  SOURCE_PATH ${SOURCE_PATH}
  OPTIONS
    -DBUILD_SHARED_LIBS=ON
    -DESPEAK_COMPAT=ON
    -DSONIC_INC=1 # Pretend to have detected sonic library, and not use it.
    -DSONIC_LIB=1
    -DUSE_ASYNC=OFF
    -DUSE_KLATT=OFF
    -DUSE_LIBPCAUDIO=OFF
    -DUSE_LIBSONIC=OFF
    -DUSE_MBROLA=OFF
    -DUSE_SPEECHPLAYER=OFF
)
vcpkg_cmake_install()
vcpkg_install_copyright(
  FILE_LIST
    "${SOURCE_PATH}/COPYING"
    "${SOURCE_PATH}/COPYING.APACHE"
    "${SOURCE_PATH}/COPYING.BSD2"
    "${SOURCE_PATH}/COPYING.UCD"
)
