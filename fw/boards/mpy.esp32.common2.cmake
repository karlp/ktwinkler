#####
# Everything below here is copied from upstream, basically, just variants stripped out
# and lockfile comparisons stripped out
# We'd really like it to have more of it moved to esp32_common.cmake so we can include it easier...
# (We're still generating lockfiles, which seems pretty pointless when there's nothign to compare them with)

# Define the output sdkconfig so it goes in the build directory.
set(SDKCONFIG ${CMAKE_BINARY_DIR}/sdkconfig)


# Include board config; this is expected to set SDKCONFIG_DEFAULTS (among other options).
include(${MICROPY_BOARD_DIR}/mpconfigboard.cmake)


# Concatenate all sdkconfig files into a combined one for the IDF to use.
file(WRITE ${CMAKE_BINARY_DIR}/sdkconfig.combined.in "")
foreach(SDKCONFIG_DEFAULT ${SDKCONFIG_DEFAULTS})
    file(READ ${SDKCONFIG_DEFAULT} CONTENTS)
    file(APPEND ${CMAKE_BINARY_DIR}/sdkconfig.combined.in "${CONTENTS}")
endforeach()
configure_file(${CMAKE_BINARY_DIR}/sdkconfig.combined.in ${CMAKE_BINARY_DIR}/sdkconfig.combined COPYONLY)
set(SDKCONFIG_DEFAULTS ${CMAKE_BINARY_DIR}/sdkconfig.combined)

# Include main IDF cmake file.
include($ENV{IDF_PATH}/tools/cmake/project.cmake)

# Generate individual dependencies.lock files based on chip target
set(LOCKFILE_PATH dependencies.lock.${IDF_TARGET})
idf_build_set_property(DEPENDENCIES_LOCK ${LOCKFILE_PATH})

##### Karl extra magic to autocreate mpconfigboard.h automatically
# Instead of having yet another file to manually update when making new boards
if(NOT DEFINED MICROPY_HW_BOARD_NAME)
    cmake_path(GET CMAKE_CURRENT_SOURCE_DIR FILENAME MICROPY_HW_BOARD_NAME)
endif()
if(NOT DEFINED MICROPY_HW_MCU_NAME)
    set(MICROPY_HW_MCU_NAME "${IDF_TARGET}")
endif()
configure_file(
    "${CMAKE_CURRENT_LIST_DIR}/mpconfigboard.h.in"
    "${MICROPY_BOARD_DIR}/mpconfigboard.h"
)