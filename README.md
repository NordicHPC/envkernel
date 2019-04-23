# Switch environments before running Jupyter kernels

Sometimes, one needs to execute Jupyter kernels in a different
environment.  One could manually adjust the kernelspec files to set
environment variables or run commands before starting the kernel, but
envkernel automates this process.


## Installation

```
pip install https://github.com/AaltoScienceIT/envkernel/archive/master.zip
```

Not currently distributed through other channels, but hopefully this
will change.  This is a single-file script and can be copied just like
this.  The script must be available both when a kernel is set up, and
each time the kernel is started (and currently assumes they are in the
same location).



## General usage and common arguments

In general, there are two passes: First, install the kernel:
`envkernel lmod --name=anaconda3 anaconda3`.  This parses some options
and writes a kernel file with the the `--name` you specify.  When
Jupyter tries to start this kernel, it will execute the next phase.

Then, when Jupyter tries to run the kernel, it will re-exec
`envkernel` in the run mode, which does whatever is needed to set up
the environment (in this case, load the `anaconda3` module).  Then it
starts the normal IPython kernel.

General arguments usable by *all* classes during the setup phase:

* `--name $name`: Name of kernel to install (**required**)
* `--user`: Install kernel into user directory
* `--prefix`: same as normal kern
* `--display-name $name`: Name to use when displaying in list
* `--replace`: Replace existing kernel?



## Docker



## Singularity

### Singularity mode arguments

* `image`: Required positional argument: run this singularity image.

* `--pwd`: Bind-mount the current working directory and use it as the
  current working directory inside the notebook.  This may happen by
  default if you don't `--contain`.

Any unknown argument is passed directly to the `singularity exec` call, and thus can be any normal Singularity arguments.  Recommend ones:

* `--contain` or `-c`: Don't share any filesystems by default.

* `--bind src:dest[:ro]`: Bind mount `src` from the host to `dest` in
  the container.  `:ro` is optional, and defaults to `rw`.

* `--cleanenv`: Clean all environment before executing.

* `--net` or `-n`: Run in new network namespace.  This does NOT work,
  because localhost must currently be shared.



## Lmod

The Lmod envkernel will load/unload
[Lmod](https://lmod.readthedocs.io/) modules before running a normal
IPython kernel inside.

### Example

```
envkernel lmod --name=anaconda3 --purge anaconda3
```

### Lmod mode Arguments

* `module ...`: Modules to load (positional argument).  Note that if
   the module is prefixed with `-`, it is actually unloaded (this is a
   Lmod feature)

* `--purge`: Purge all modules before loading the new modules.
