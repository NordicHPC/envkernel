# Switch environments before running Jupyter kernels

Sometimes, one needs to execute Jupyter kernels in a different
environment.  Say you want to execute the kernel in a conda
environment (that's easy, but actually misses setting certain
environment variables).  Or run it inside a Docker container.  One
could manually adjust the kernelspec files to set environment
variables or run commands before starting the kernel, but envkernel
automates this process.

envkernel is equally usable for end users (on their own systems or
clusters) to easily access environments in Jupyter, or sysadmins
deploying this access on systems they administer.

In general, there are two passes: First, install the kernel, e.g.:
`envkernel virtualenv --name=my-venv /path/to/venv`.  This parses some
options and writes a kernelspec file with the the `--name` you
specify.  When Jupyter tries to start this kernel, it will execute the
next phase.  When Jupyter tries to run the kernel, the kernelspec file
will re-execute `envkernel` in the run mode, which does whatever is
needed to set up the environment (in this case, sets `PATH` to the
`/path/to/venv/bin/` that is needed).  Then it starts the normal
IPython kernel.

Available modes:
* `conda`: Activate a [conda environment](https://docs.conda.io/) first.
* `virtualenv`: Activate a virtualenv first.
* `docker`: Run the kernel in a Docker container.
* `singularity`: Run the kernel in a [singularity container](https://www.sylabs.io/docs/).
* `Lmod`: Activate [Lmod](https://lmod.readthedocs.io/) modules first.





## Installation

Available on the PiPI: `pip install envkernel`.

Or, you can install latest from Github in the usual way: `pip install https://github.com/NordicHPC/envkernel/archive/master.zip`

This is a single-file script and can be copied directly and added to
`PATH` as well.  By design, there are no dependencies except the basic
Jupyter client (not notebook or any UI).  The script must be available both when a kernel is set up, and
each time the kernel is started (and currently assumes they are in the
same location).





## General usage and common arguments

General invocation:

```shell
envkernel [mode] [envkernel options] [mode-specific-options]
```


General arguments usable by *all* classes during the setup phase:

These options directly map to normal Jupyter kernel install options:

* `mode`: `singularity`, `docker`, `lmod`, or whatever mode is desired.
* `--name $name`: Name of kernel to install (**required**).
* `--user`: Install kernel into user directory.
* `--sys-prefix`: Install to the current Python's `sys.prefix` (the Python which is running envkernel).
* `--prefix`: same as normal kernel install option.
* `--display-name NAME`: Human-readable name.
* `--replace`: Replace existing kernel (Jupyter option, unsure what this means).
* `--language`: What language to tag this kernel (default `python`).

These are envkernel-specific options:

* `--python`: Python interpreter to use when invoking inside the
  environment. (Default `python`.  Unlike other kernels, this defaults
  to a relative path because the point of envkernel is to set up PATH
  properly.)  If this is the special value `SELF`, this will be replaced
  with the value of `sys.executable` of the Python running envkernel.
* `--kernel=NAME`: Auto-set `--language` and `--kernel-cmd` to
  that needed for these well-known kernels.  Options include `ipykernel` (the default) or `ir`.
* `--kernel-cmd`: a string which is the kernel to start - space
  separated, no shell quoting, it will be split when saving.  The
  default is `python -m ipykernel_launcher -f {connection_file}`,
  which is suitable for IPython.  For example, to start an R kernel in
  the environment use `R --slave -e IRkernel::main() --args
  {connection_file}` as the value to this, being careful with quoting
  the spaces only once.  To find what the strings should be, copy form
  some existing kernels.  `--kernel=NAME` includes shortcut for some
  popular kernels.
* `--kernel-template`: An already-installed kernel name which is used
  as a template for the new envkernel.  This is searched using the
  normal Jupyter search paths.  This kernel json file is loaded and
  used as a template for all kernel options (`--language`,
  `--kernel-cmd`, etc).  Also, any other file in this directory (such
  as logos) are copied to the new kernel (like kernel.js in irkernel).
* `--env=NAME=VALUE`.  Set these environment variables when running
  the kernel.  These are actually just saved in the `kernel.json` file
  under the `env` key, which is used by Jupyter itself.  So, this is
  just a shorthand for adding variables there, it is not used at the
  envkernel stage at all.

Order of precedence of options (later in the list overrides earlier):
`--kernel-template`, `--kernel`, `--kernel-cmd`, `--language`,
`--python`, `--display-name`.




## Conda

The Conda envkernel will activate Conda environments (set the `PATH`,
`CPATH`, `LD_LIBRARY_PATH`, and `LIBRARY_PATH` environment variables).
This is done manually, if anyone knows a better way to do this, please
inform us.

### Conda example

This will load the `anaconda` environment before invoking an IPython
kernel using the name `python`, which will presumably be the one
inside the `anaconda3` environment.

```shell
envkernel conda --name=conda-anaconda3 /path/to/anaconda3
```

### Conda mode arguments

General invocation:

```shell
envkernel conda --name=NAME [envkernel options] conda-env-full-path
```

* `conda-env-full-path`: Full path to the conda environment to load.





## Virtualenv

This operates identically to `conda` mode, but with name `virtualenv`
on virtualenvs.

### Virtualenv example

```shell
envkernel virtualenv --name=conda-anaconda3 /path/to/anaconda3
```





## Docker

Docker is a containerization system that runs as a system service.

Note: docker has not been fully tested, but has been reported to work.


### Docker example

```shell
envkernel docker --name=NAME  --pwd --bind /m/jh/coursedata/:/coursedata /path/to/image.simg
```

### Docker mode arguments

General invocation:

```shell
envkernel docker --name=NAME [envkernel options] [docker options] [image]
```

* `image`: Required positional argument: name of docker image to run.

* `--pwd`: Bind-mount the current working directory and use it as the
  current working directory inside the notebook.  This is usually
  useful.

* A few more yet-undocumented and untested arguments...

Any unknown argument is passed directly to the `docker run` call, and
thus can be any normal Docker argument.  If `,copy` is included in the
`--mount` command options, the directory will be copied before
mounting.  This may be useful if the directory is on a network mount
which the root docker can't access.





## Singularity

[Singularity](https://www.sylabs.io/docs/) is a containerization
system somewhat similar to Docker, but designed for user-mode usage
without root, and with a mindset of using user software instead of
system services.


### Singularity example

```shell
envkernel singularity --name=NAME --contain --bind /m/jh/coursedata/:/coursedata /path/to/image.simg
```

### Singularity mode arguments

General invocation:

```shell
envkernel singularity --name=NAME [envkernel options] [singularity options] [image]
```

* `image`: Required positional argument: name of singularity image to
  run.

* `--pwd`: Bind-mount the current working directory and use it as the
  current working directory inside the notebook.  This may happen by
  default if you don't `--contain`.

Any unknown argument is passed directly to the `singularity exec`
call, and thus can be any normal Singularity arguments.  The most
useful Singularity options are (nothing envkernel specific here):

* `--contain` or `-c`: Don't share any filesystems by default.

* `--bind src:dest[:ro]`: Bind mount `src` from the host to `dest` in
  the container.  `:ro` is optional, and defaults to `rw`.

* `--cleanenv`: Clean all environment before executing.

* `--net` or `-n`: Run in new network namespace.  This does **NOT**
  work with Jupyter kernels, because localhost must currently be
  shared.  So don't use this unless we create proper net gateway.





## Lmod

The Lmod envkernel will load/unload
[Lmod](https://lmod.readthedocs.io/) modules before running a normal
IPython kernel.

Using envkernel is better than the naive (but functional) method of
modifying a kernel to invoke a particular Python binary, because that
will invoke the right Python interpreter but not set relevant other
environment variables (so, for example, subprocesses won't be in the
right environment).

### Lmod example

This will run `module purge` and then `module load anaconda3` before
invoking an IPython kernel using the name `python`, which will
presumably be the one inside the `anaconda3` environment.

```shell
envkernel lmod --name=anaconda3 --purge anaconda3
```

### Lmod mode arguments

General invocation:

```shell
envkernel lmod --name=NAME [envkernel options] [module ...]
```

* `module ...`: Modules to load (positional argument).  Note that if
   the module is prefixed with `-`, it is actually unloaded (this is a
   Lmod feature).

* `--purge`: Purge all modules before loading the new modules.  This
  can be safer, because sometimes users may automatically load modules
  from their `.bashrc` which will cause failures if you try to load
  conflicting ones.





## How it works

When envkernel first runs, it sets up a kernelspec that will re-invoke
envkernel when it runs.  Some options are when firs run (kernelspec
name and options), while usually most are passed through straight to
the kernelspec.  When the kernel is started, envkernel is re-invoked

Example envkernel setup command.  This makes a new Jupyter kernel
(`envkernel singularity` means singularity create mode) named
`testcourse-0.5.9` out of the image `/l/simg/0.5.9.simg` with the
Singularity options `--contain` (contain, on default mounts) and
`--bind` (bind a dir).`

```shell
envkernel singularity --sys-prefix --name=testcourse-0.5.9 /l/simg/0.5.9.simg --contain --bind /m/jh/coursedata/:/coursedata
```

That will create this kernelspec.  Note that most of the arguments are passed through:

```json
{
    "argv": [
        "/opt/conda-nbserver-0.5.9/bin/envkernel",
        "singularity",
        "run",
        "--connection-file",
        "{connection_file}",
        "--contain",
        "--bind",
        "/m/jh/coursedata/:/coursedata",
        "/l/simg/0.5.9.simg",
        "--",
        "python",
        "-m",
        "ipykernel_launcher",
        "-f",
        "{connection_file}"
    ],
    "display_name": "Singularity with /l/simg/0.5.9.simg",
    "language": "python"
}
```

When this runs, it runs `singularity --contain --bind
/m/jh/coursedata/:/coursedata /l/simg/0.5.9.simg`.  Inside the image,
it runs `python -m ipykernel_launcher -f {connection_file}`.
envkernel parses and manipulates these arguments however is needed.





## Running multiple modes

envkernel doesn't support running multiple modes - for example,
`conda` and `lmod` at the same time.  But, because of the general
nature, you should be able to layer it yourself.  The following
example uses the `conda` mode to create an envkernel.  Then, it uses
`--kernel-template` to re-read that kernel and wrap it in `lmod`:

```
envkernel conda --name=test1 conda_path
envkernel lmod --name=test1 --kernel-template=test1 lmod_module
```

There is nothing really special here, it is layering one envkernel
execution on top of another.  If you notice problems with this, please
try to debug a bit and then send feedback/improvements, this is a
relatively new feature.





## Use with nbgrader

envkernel was orginally inspired by the need for nbgrader to securely
contain student's code while autograding.  To do this, set up a
contained kernel as above - it's up to you to figure out how to do
this properly with your chosen method (docker or singularity).  Then
autograde like normal, but add the `--ExecutePreprocessor.kernel_name`
option.

Set up a kernel:

```shell
envkernel docker --user --name=testcourse-0.5.9 --pwd aaltoscienceit/notebook-server:0.5.9 --bind /mnt/jupyter/course/testcourse/data/:/coursedata
```

Run the autograding:

```shell
nbgrader autograde --ExecutePreprocessor.kernel_name=testcourse-0.5.9 R1_Introduction

```





## See also

* General
  * [a2km, "Assistant to the kernel manager"](https://github.com/minrk/a2km) is a command line tool for dealing with kernels, including making kernels which activate conda/venv kernels.  And some other handy kernel manipulations stuff.  Unfortunately written in Ruby.
  * https://github.com/Anaconda-Platform/nb_conda_kernels - automatically create kernels from conda environments.  Uses a KernelSpecManager so possibly overrides everything at once, and also defaults to all kernels.
  * The direct way to make a conda/virtualenv available in Jupyter is to activate the environment, then run `python -m ipykernel install [--user|--prefix=/path/to/other/env/]`.  But this does *not* set up `PATH`, so calling other executables doesn't work... thus the benefit of envkernel.
  * [This thread](https://groups.google.com/forum/#!topic/jupyter/kQ9ZDX4rDEE) was the clue to getting a kernel inside Docker working.




## Development and contributions

Developed at Aalto University Science-IT.  Primary contact: Richard
Darst.  Contributions welcome from anyone.  As of early 2019, it is
mid 2019, it's usable but there may be bugs as it gets used in more
sites.
