import sys
from os.path import isdir, join
from os import listdir
import re
import difflib

from SCons.Script import DefaultEnvironment

env = DefaultEnvironment()
platform = env.PioPlatform()
board = env.BoardConfig()

FRAMEWORK_DIR = platform.get_package_dir("framework-py32f0sdk")
assert isdir(FRAMEWORK_DIR)

lib_dir = join(FRAMEWORK_DIR, 'libraries')

mcu_long = board.get('build.mcu', '').upper()  # e.g. PY32F003X8
mcu_short = re.findall(r'PY32F\d\d\d[AB]?', mcu_long)[0]  # PY32F003

if mcu_short == 'PY32F002B':
    dir_prefix = 'PY32F002B'
elif mcu_short.startswith('PY32F07'):
    dir_prefix = 'PY32F07x'
else:
    dir_prefix = 'PY32F0xx'

cmsis_dir = join(FRAMEWORK_DIR, 'CMSIS')

need_hal = '-DUSE_HAL_DRIVER' in env['BUILD_FLAGS']
if need_hal:
    driver_dir = join(FRAMEWORK_DIR, dir_prefix+'_HAL_Driver')
    bsp_dir = join(FRAMEWORK_DIR, dir_prefix+'_HAL_BSP')
else:
    driver_dir = join(FRAMEWORK_DIR, dir_prefix+'_LL_Driver')
    bsp_dir = join(FRAMEWORK_DIR, dir_prefix+'_LL_BSP')

machine_flags = [
    '-mthumb',
    '-mcpu={}'.format(board.get('build.cpu')),
]


env.Append(
    ASFLAGS=machine_flags,
    ASPPFLAGS=['-x', 'assembler-with-cpp'],

    CCFLAGS=machine_flags + [
        "-Os",  # optimize for size
        "-ffunction-sections",  # place each function in its own section
        "-fdata-sections",
        "-Wall",
        "-nostdlib",
    ],

    CXXFLAGS=[
        "-fno-rtti",
        "-fno-exceptions",
        "-fno-threadsafe-statics",
        '-Wno-register',
    ],

    CPPDEFINES=[
        mcu_long,
        mcu_short,
        'PY32F0',
        'PY32F0xx'
    ],

    # includes
    CPPPATH=[
        join(cmsis_dir, 'Core', 'Include'),
        join(cmsis_dir, 'Device', 'PY32F0xx', 'Include'),
        join(driver_dir, 'Inc'),
        env.subst("${PROJECT_INCLUDE_DIR}"),  # place for py32f0xx_hal_conf.h
    ],
    LINKFLAGS=machine_flags + [
        "-Os",
        "-Wl,--gc-sections",
        "--specs=nano.specs",
        "--specs=nosys.specs",
        "-static",
        "-Wl,--check-sections",
        "-Wl,--unresolved-symbols=report-all",
        "-Wl,--warn-common",
    ],

    # LIBSOURCE_DIRS=[join(FRAMEWORK_DIR, 'libraries')],

    LIBS=["c", "m"],

)

need_bsp = '-DUSE_BSP' in env['BUILD_FLAGS']

if need_bsp:
    env.Append(
        CPPPATH=[join(bsp_dir, 'Inc')],
    )


# env.Append(
#     ASFLAGS=env.get("CCFLAGS", [])[:]
# )

def parse_ld_num(v: str):
    if v.endswith('K'):
        return int(v[:-1]) * 1024
    elif v.endswith('M'):
        return int(v[:-1]) * 1024 * 1024
    else:
        return int(v, 0)


def get_linker_sizes(ld_file: str):
    """Very hacky way to read flash/ram size from ld file. """
    try:
        with open(ld_file, 'r', encoding='utf-8') as f:
            all = f.read()
            flash = re.findall(r'FLASH.*ORIGIN\s*=\s*(\w*),\s*LENGTH\s*=\s*(\w*)', all)[0]
            ram = re.findall(r'RAM.*ORIGIN\s*=\s*(\w*),\s*LENGTH\s*=\s*(\w*)', all)[0]
            return parse_ld_num(flash[1]), parse_ld_num(ram[1])
    except IndexError:
        return None
    return None


ldscript = board.get('build.ldscript', '')
if not ldscript:
    raise RuntimeError('Board has no ldscript!')
ldscript = join(FRAMEWORK_DIR, 'ldscripts', ldscript)
env.Replace(LDSCRIPT_PATH=ldscript)

sizes = get_linker_sizes(ldscript)
board.update("upload.maximum_size", str(sizes[0]))
board.update("upload.maximum_ram_size", str(sizes[1]))

env.BuildSources(
    join('$BUILD_DIR', 'Driver'),
    join(driver_dir, 'Src'),
)

if need_bsp:
    env.BuildSources(
        join('$BUILD_DIR', 'BSP'),
        join(bsp_dir, 'Src'),
    )


libs = []


def select_best_file(path, filemask, mcu):
    presize_file = filemask.format(mcu)  # e.g. system_py32f003.c
    filemask = filemask.format('.*')
    files = [p for p in listdir(path) if re.match(filemask, p)]

    for f in files:
        if re.match(f.replace('x', '.'), presize_file):
            return f
    return None


cmsis_src_dir = join(cmsis_dir, 'Device', 'PY32F0xx', 'Source')
sys_file = select_best_file(cmsis_src_dir, 'system_{}.c', mcu_short.lower())
libs.append(
    env.BuildLibrary(
        join("$BUILD_DIR", "FrameworkCMSISDevice"),
        cmsis_src_dir,
        src_filter=[
            '-<*>',
            '+<gcc/startup_{}.s>'.format(mcu_short.lower()),
            '+<{}>'.format(sys_file),
        ],
    )
)

env.Prepend(LIBS=libs)
