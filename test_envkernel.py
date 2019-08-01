import json
import os
from os.path import join as pjoin
import pytest
import shlex
import subprocess
import sys
import tempfile

import envkernel

sys.argv[0] = 'envkernel'

TEST_CONNECTION_FILE = """\
{
  "shell_port": 10000,
  "iopub_port": 10001,
  "stdin_port": 10002,
  "control_port": 10003,
  "hb_port": 10004,
  "ip": "127.0.0.1",
  "key": "00000000-000000000000000000000000",
  "transport": "tcp",
  "signature_scheme": "hmac-sha256",
  "kernel_name": ""
}
"""
ALL_MODULES = ["conda", "virtualenv", "lmod", "docker", "singularity"]


def install(d, argv, name='testkernel'):
    """Run envkernel setup, return dict with properties"""
    if isinstance(argv, str):
        argv = shlex.split(argv)
    argv.insert(0, 'envkernel')
    argv[2:2] = ['--name', name, '--prefix', d]
    envkernel.main(argv)
    return get(d, name)

def get(d, name):
    dir_ = pjoin(d, 'share/jupyter/kernels/', name)
    kernel = json.load(open(pjoin(dir_, 'kernel.json')))
    return {
        'dir': dir_,
        'kernel': kernel,
        'ek': envkernel.split_doubledash(kernel['argv'])[0],
        'k': envkernel.split_doubledash(kernel['argv'])[1],
        }

def run(d, kern, execvp=lambda _argv0, argv: 0):
    connection_file = pjoin(d, 'connection.json')
    open(connection_file, 'w').write(TEST_CONNECTION_FILE)
    # Do basic tests
    argv = kern['kernel']['argv']
    clsname = argv[1]
    assert argv[2] == 'run'
    # Replace connecton file
    def replace_conn_file(x):
        if x == '{connection_file}':  return connection_file
        else:  return x
    argv = [ replace_conn_file(x) for x in argv ]
    # Setup object, override the execvp for the function, run.
    ek = getattr(envkernel, clsname)(argv[3:])
    ek.execvp = execvp
    ek.run()

@pytest.fixture(scope='function')
def d():
    """Temporary directory for test"""
    with tempfile.TemporaryDirectory() as dir_:
        yield dir_

def all_modes(modes=None):
    if not modes:
        modes = ALL_MODULES
    return pytest.mark.parametrize("mode", modes)

def is_sublist(list_, sublist):
    """A sublist is part of a given list"""
    return any(list_[i:i+len(sublist)] == sublist
               for i in range(len(list_)-len(sublist)+1))




@all_modes()
def test_basic(d, mode):
    kern = install(d, "%s MOD1"%mode)
    #assert kern['argv'][0] == 'envkernel'  # defined above
    assert kern['ek'][1:3] == [mode, 'run']

@all_modes()
def test_display_name(d, mode):
    kern = install(d, "%s --display-name=AAA MOD1"%mode)
    assert kern['kernel']['display_name'] == 'AAA'

@all_modes(['conda'])
def test_template(d, mode):
    subprocess.call("python -m ipykernel install --name=aaa-ipy --display-name=BBB --prefix=%s"%d, shell=True)
    #os.environ['ENVKERNEL_TESTPATH'] = os.path.join(d, 'share/jupyter/kernels')
    os.environ['JUPYTER_PATH'] = pjoin(d, 'share/jupyter')
    kern = install(d, "%s --kernel-template aaa-ipy MOD1"%mode)
    assert kern['kernel']['display_name'] == 'BBB'

def test_help():
    """Test that the global -h option works and prints module names"""
    p = subprocess.Popen("python -m envkernel -h", shell=True, stdout=subprocess.PIPE)
    stdout = p.stdout.read().decode()
    p.wait()
    for mod in ALL_MODULES:
        assert mod in stdout, "%s not found in --help output"%mod
    assert p.returncode == 0

def test_umask(d):
    orig_umask = os.umask(0)
    # Test multiple umasks, and kerneldir + kernel.json
    for umask in [0, 0o022]:
        os.umask(umask)
        kern = install(d, "lmod MOD1")
        assert os.stat(kern['dir']).st_mode & 0o777  ==  0o777&(~umask)
        assert os.stat(pjoin(kern['dir'], 'kernel.json')).st_mode & 0o777  ==  0o666&(~umask)
    os.umask(orig_umask)


@all_modes()
def test_set_python(d, mode):
    kern = install(d, "%s --python=AAA MOD1"%mode)
    assert kern['k'][0] == 'AAA'

@all_modes()
def test_set_kernel_cmd(d, mode):
    kern = install(d, "%s --kernel-cmd='a b c d' MOD1"%mode)
    assert kern['k'] == ['a', 'b', 'c', 'd']

@all_modes()
def test_language(d, mode):
    kern = install(d, "%s --language=AAA MOD1"%mode)
    assert kern['kernel']['language'] == 'AAA'

@all_modes()
def test_env(d, mode):
    kern = install(d, "%s --env=AAA=BBB --env=CCC=DDD MOD1"%mode)
    assert kern['kernel']['env']['AAA'] == 'BBB'
    assert kern['kernel']['env']['CCC'] == 'DDD'



# Languages
@all_modes()
def test_default_language(d, mode):
    # default language is ipykernel
    kern = install(d, "%s MOD1"%mode)
    assert kern['kernel']['language'] == 'python'
    assert kern['k'][0] == 'python'
    assert kern['k'][1:4] == ['-m', 'ipykernel_launcher', '-f']

@all_modes()
def test_ipykernel(d, mode):
    kern = install(d, "%s --kernel=ipykernel MOD1"%mode)
    assert kern['kernel']['language'] == 'python'
    assert kern['k'][0] == 'python'
    assert kern['k'][1:4] == ['-m', 'ipykernel_launcher', '-f']

@all_modes()
def test_ir(d, mode):
    kern = install(d, "%s --kernel=ir MOD1"%mode)
    assert kern['kernel']['language'] == 'R'
    assert kern['k'][0] == 'R'
    assert kern['k'][1:5] == ['--slave', '-e', 'IRkernel::main()', '--args']

@all_modes()
def test_imatlab(d, mode):
    kern = install(d, "%s --kernel=imatlab MOD1"%mode)
    assert kern['kernel']['language'] == 'matlab'
    assert kern['k'][0].endswith('python')
    assert kern['k'][1:4] == ['-m', 'imatlab', '-f']



# Test setting up specific kernels
def test_lmod(d):
    kern = install(d, "lmod MOD1 MOD2")
    #assert kern['argv'][0] == 'envkernel'  # defined above
    assert kern['ek'][1:3] == ['lmod', 'run']
    assert kern['ek'][-2] == 'MOD1'
    assert kern['ek'][-1] == 'MOD2'

def test_lmod_purge(d):
    kern = install(d, "lmod --purge MOD3")
    #assert kern['argv'][0] == 'envkernel'  # defined above
    assert '--purge' in kern['ek'][3:]
    assert kern['ek'][-1] == 'MOD3'

def test_conda(d):
    kern = install(d, "conda /PATH/BBB")
    #assert kern['argv'][0] == 'envkernel'  # defined above
    assert kern['ek'][1:3] == ['conda', 'run']
    assert kern['ek'][-1] == '/PATH/BBB'

def test_virtualenv(d):
    kern = install(d, "virtualenv /PATH/CCC")
    #assert kern['argv'][0] == 'envkernel'  # defined above
    assert kern['ek'][1:3] == ['virtualenv', 'run']
    assert kern['ek'][-1] == '/PATH/CCC'

def test_docker(d):
    kern = install(d, "docker --some-arg=AAA IMAGE1")
    #assert kern['argv'][0] == 'envkernel'  # defined above
    assert kern['ek'][1:3] == ['docker', 'run']
    assert kern['ek'][-1] == 'IMAGE1'
    assert '--some-arg=AAA' in kern['ek']

def test_singularity(d):
    kern = install(d, "singularity --some-arg=AAA /PATH/TO/IMAGE2")
    #assert kern['argv'][0] == 'envkernel'  # defined above
    assert kern['ek'][1:3] == ['singularity', 'run']
    assert kern['ek'][-1] == '/PATH/TO/IMAGE2'
    assert '--some-arg=AAA' in kern['ek']



# Test running kernels
def test_run_conda(d):
    PATH = pjoin(d, 'test-conda')
    os.mkdir(PATH)
    os.mkdir(pjoin(PATH, 'bin'))

    def test_exec(_file, _args):
        assert pjoin(PATH, 'bin') in os.environ['PATH'].split(':')
        assert pjoin(PATH, 'include') in os.environ['CPATH'].split(':')
        assert pjoin(PATH, 'lib') in os.environ['LD_LIBRARY_PATH'].split(':')
        assert pjoin(PATH, 'lib') in os.environ['LIBRARY_PATH'].split(':')
    kern = install(d, "conda %s"%PATH)
    run(d, kern, test_exec)

def test_run_venv(d):
    PATH = pjoin(d, 'test-venv')
    os.mkdir(PATH)
    os.mkdir(pjoin(PATH, 'bin'))

    def test_exec(_file, _args):
        assert pjoin(PATH, 'bin') in os.environ['PATH'].split(':')
    kern = install(d, "conda %s"%PATH)
    run(d, kern, test_exec)

# Requires lmod installed... and a module to exist
#def test_run_lmod(d):

def test_run_docker(d):
    def test_exec(_file, argv):
        assert argv[0:5] == ['docker', 'run', '--rm', '-i', '--user']
        for port in range(10000, 10005):
            assert '--expose=%d'%port in argv
            assert is_sublist(argv, ['-p', '%d:%d'%(port, port)])
        assert '--some-arg=AAA' in argv
        assert 'IMAGE' in argv
        i = argv.index('-f')
        assert json.loads(open(argv[i+1]).read())['ip'] == '0.0.0.0'
        connection_file = pjoin(d, 'connection.json')
        assert is_sublist(argv, ["--mount", "type=bind,source=%s,destination=%s,ro=false"%(connection_file, connection_file)])
    kern = install(d, "docker --some-arg=AAA IMAGE")
    run(d, kern, test_exec)

    # Test the --pwd option, and also that it does not go when it is NOT present
    pwd_mount = ["--mount", "type=bind,source=%s,destination=%s,ro=false"%(os.getcwd(), os.getcwd())]
    def test_exec(_file, argv):
        assert is_sublist(argv, pwd_mount)
    kern = install(d, "docker --some-arg=AAA --pwd IMAGE")
    run(d, kern, test_exec)
    # Test above, but reversed
    def test_exec(_file, argv):
        assert not is_sublist(argv, pwd_mount)
    kern = install(d, "docker --some-arg=AAA IMAGE")
    run(d, kern, test_exec)
    # Custom workdir
    pwd_mount = ["--mount", "type=bind,source=%s,destination=%s,ro=false"%(os.getcwd(), '/WORKDIR')]
    def test_exec(_file, argv):
        assert is_sublist(argv, pwd_mount)
    kern = install(d, "docker --some-arg=AAA --workdir=/WORKDIR IMAGE")
    run(d, kern, test_exec)


def test_run_singularity(d):
    def test_exec(_file, argv):
        assert argv[0] == 'singularity'
        assert '--some-arg=AAA' in argv
        assert 'IMAGE' in argv
    kern = install(d, "singularity --some-arg=AAA IMAGE")
    run(d, kern, test_exec)

    def test_exec(_file, argv):
        assert argv[0] == 'singularity'
        assert is_sublist(argv, ['--bind', os.getcwd()])
        assert is_sublist(argv, ['--pwd', os.getcwd()])
        #assert is_sublist(argv, ['--bind', '/PATH/AAA:/PATH/AAA'])
    kern = install(d, "singularity --pwd IMAGE")
    run(d, kern, test_exec)
