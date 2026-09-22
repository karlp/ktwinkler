# Ensure MICROPY_DIR is set, and then just include the normal main component
get_filename_component(PROJECT_DIR "../../.." ABSOLUTE)
set(MICROPY_DIR ${PROJECT_DIR}/lib/micropython)

include (${MICROPY_DIR}/ports/esp32/main/CMakeLists.txt)
