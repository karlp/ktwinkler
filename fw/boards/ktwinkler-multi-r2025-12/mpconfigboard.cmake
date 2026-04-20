# Define the chip variant.
set(IDF_TARGET esp32c3)

# Set the sdkconfig fragments.
set(SDKCONFIG_DEFAULTS
    ${MICROPY_PORT_DIR}/boards/sdkconfig.base
    ${MICROPY_PORT_DIR}/boards/sdkconfig.ble
    sdkconfig.board
)

include($ENV{IDF_PATH}/tools/cmake/version.cmake)
set(IDF_VERSION "${IDF_VERSION_MAJOR}.${IDF_VERSION_MINOR}.${IDF_VERSION_PATCH}")

# Set the user C modules to include in the build.
#set(USER_C_MODULES
#    ${PROJECT_DIR}/src/cmodules/cexample/micropython.cmake
#    ${PROJECT_DIR}/src/cmodules/cexample2/micropython.cmake
#)

# Set the manifest file for frozen Python code.
set(MICROPY_FROZEN_MANIFEST ${MICROPY_BOARD_DIR}/manifest.py)
