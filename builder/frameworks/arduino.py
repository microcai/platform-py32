import sys
from os.path import exists,isdir, isfile, join
from string import Template

from SCons.Script import DefaultEnvironment

env = DefaultEnvironment()
platform = env.PioPlatform()
board = env.BoardConfig()
mcu = board.get("build.mcu", "")
product_line = board.get("build.product_line", "")
bsp = board.get("build.bsp", "")
maximum_size = board.get("upload.maximum_size", "65536")
maximum_ram_size = board.get("upload.maximum_ram_size", "1024")
env.SConscript("_bare.py")

FRAMEWORK_DIR = platform.get_package_dir("Arduino-PY32")
assert isdir(FRAMEWORK_DIR)

FRAMEWORK_LIB_DIR = join(FRAMEWORK_DIR, "libraries")
assert isdir(FRAMEWORK_LIB_DIR)

FRAMEWORK_VARIANTS_DIR = join(FRAMEWORK_DIR, "variants", bsp.upper() + "xx", bsp.upper() + "_Base")


def get_linker_script():
    ldscript = join(FRAMEWORK_VARIANTS_DIR, "ldscript.ld")

    if isfile(ldscript):
        return ldscript

    sys.stderr.write("Warning! Cannot find a linker script for the required board! "+ldscript)

libs = []

env.Append(
    CPPPATH=[
        FRAMEWORK_VARIANTS_DIR,
        FRAMEWORK_LIB_DIR,
        join(FRAMEWORK_DIR, "cores", "arduino"),
        join(FRAMEWORK_DIR, "cores", "arduino", "py32"),
        join(FRAMEWORK_DIR, "cores", "arduino", "py32", "usb"),
        join(FRAMEWORK_DIR, "cores", "arduino", "py32", "LL"),
        join(FRAMEWORK_DIR, "system", "Arduino-PY32F0xx-Drivers", "CMSIS", "Include"),
        join(FRAMEWORK_DIR, "system", "Arduino-PY32F0xx-Drivers", "CMSIS", "Device", "PY32F0xx", "Include"),
        join(FRAMEWORK_DIR, "system", "Arduino-PY32F0xx-Drivers", "PY32F0xx_HAL_Driver", "Inc"),
        join(FRAMEWORK_DIR, "system", "PY32F0xx"),
        join(FRAMEWORK_LIB_DIR, "Arduino", "inc"),
        join(FRAMEWORK_LIB_DIR, "Wire", "src"),
        join(FRAMEWORK_LIB_DIR, "SPI", "src"),
        join(FRAMEWORK_DIR, "system", "Arduino-PY32F0xx-Drivers", "CMSIS", "Device", "PY32F0xx", "Source", "gcc"),
    ]
)

env.Append(
    CPPDEFINES=[
        "PY32F0xx",
        'VARIANT_H=\"variant_generic.h\"',
        "USE_STDPERIPH_DRIVER",
        "VDD_3V3",
        "NO_ATOMIC",
        "USE_FULL_LL_DRIVER",
        "HAL_TIM_MODULE_ENABLED",
        mcu.upper(),
        "NDEBUG",
    ]
)

env.Replace(LDSCRIPT_PATH=get_linker_script())

#
# Target: Build Firmware Library
#

extra_flags = board.get("build.extra_flags", "")

# libs.append(env.BuildLibrary(
#     join("$BUILD_DIR", "py32startup"),
#     join(FRAMEWORK_DIR, "system", "Arduino-PY32F0xx-Drivers", "CMSIS", "Device", "PY32F0xx", "Source"),
#     src_filter=[
#         "+<*.c>",
#         "+<gcc/startup_%s.s>" % bsp.lower()
#     ]
# ))

libs.append(env.BuildLibrary(
    join("$BUILD_DIR", "py32startup"),
    join(FRAMEWORK_DIR, "cores", "arduino", "py32"),
    src_filter=[
        "+<*.S>"
    ]
))

libs.append(env.BuildLibrary(
    join("$BUILD_DIR", "arduino", "libraries"),
    join(FRAMEWORK_DIR, "libraries", "SrcWrapper", "src"),
    src_filter=[
        "+<air/*.c>",
        "+<air/*.cpp>",
        "+<*.cpp>",
    ]
))

libs.append(env.BuildLibrary(
    join("$BUILD_DIR", "arduino", 'Wire'),
    join(FRAMEWORK_DIR, "libraries", "Wire", "src"),
    src_filter=[
        "+<*.c>",
        "+<*.cpp>",
        "+<utility/*.c>",
    ]
))

libs.append(env.BuildLibrary(
    join("$BUILD_DIR", "arduino"),
    join(FRAMEWORK_DIR, "cores", "arduino"),
    src_filter=[
        "+<*.c>",
        "+<*.cpp>",
    ]
))

libs.append(env.BuildLibrary(
    join("$BUILD_DIR", "arduino", "py32hal_drivers"),
    join(FRAMEWORK_DIR, "system", "Arduino-PY32F0xx-Drivers", "PY32F0xx_HAL_Driver", "Src"),
    src_filter=[
        "+<*.c>",
    ]
))

libs.append(env.BuildLibrary(
    join("$BUILD_DIR", "py32driverbase"),
    FRAMEWORK_VARIANTS_DIR,
    src_filter=[
        "+<*.c>",
        "+<*.cpp>"
    ]
))

env.Append(LIBS=libs)

env.Append(LINKFLAGS=[
    "-Wl,-Map,%s/firmware.map" % env.get("BUILD_DIR"),
    "-Wl,--defsym=LD_MAX_SIZE=%s" % maximum_size,
    "-Wl,--defsym=LD_MAX_DATA_SIZE=%s" % maximum_ram_size,
    "-Wl,--defsym=LD_FLASH_OFFSET=0",
    "-Wl,--gc-sections",
    "-Wl,--entry=Reset_Handler",
])