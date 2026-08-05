# Filesystem API Reference

## FilesystemClient (`resource.fs.*`)

All operations are **async** — they return a `Task` object. Call `.wait()` then read `.result`.

### Task Lifecycle

```python
task = resource.fs.ls("/path")
task.wait(timeout=60, poll_interval=2)  # block until done
print(task.id, task.state, task.is_terminal)
print(task.result)    # actual output data
task.refresh()        # manual status update
task.cancel()         # abort operation
```

## Read Operations

### List Directory
```python
task = resource.fs.ls("/home/user", recursive=False)
task.wait()
files = task.result  # list of entries
```

### Read File Content
```python
# First N lines
task = resource.fs.head("/home/user/output.log", lines=50)

# Last N lines
task = resource.fs.tail("/home/user/output.log", lines=10)

# Binary view (N bytes at offset)
task = resource.fs.view("/home/user/data.bin", size=4096, offset=0)
```

### File Metadata
```python
task = resource.fs.stat("/home/user/file.h5")    # size, permissions, timestamps
task = resource.fs.file("/home/user/mystery")     # detect file type
task = resource.fs.checksum("/home/user/data.h5") # compute hash
```

## Write Operations

### Create Directory
```python
task = resource.fs.mkdir("/home/user/newdir")
```

### Copy / Move / Delete
```python
task = resource.fs.cp("/home/user/src", "/home/user/dst")
task = resource.fs.mv("/home/user/old", "/home/user/new")
task = resource.fs.rm("/home/user/tmp")
```

### Symbolic Links
```python
task = resource.fs.symlink("/home/user/target", "/home/user/link")
```

## Permissions

```python
task = resource.fs.chmod("/home/user/script.sh", "755")
task = resource.fs.chown("/home/user/file", owner="user", group="staff")
```

## Archives

```python
task = resource.fs.compress("/home/user/data", "/home/user/data.tar.gz")
task = resource.fs.extract("/home/user/data.tar.gz", "/home/user/output")
```

## Complete Operations List

| Operation | Method | Description |
|-----------|--------|-------------|
| ls | `fs.ls(path, recursive=False)` | List directory |
| stat | `fs.stat(path)` | File metadata |
| head | `fs.head(path, lines=N)` | First N lines |
| tail | `fs.tail(path, lines=N)` | Last N lines |
| view | `fs.view(path, size=N, offset=M)` | Binary read |
| file | `fs.file(path)` | Detect type |
| checksum | `fs.checksum(path)` | Compute hash |
| mkdir | `fs.mkdir(path)` | Create directory |
| cp | `fs.cp(src, dst)` | Copy |
| mv | `fs.mv(src, dst)` | Move/rename |
| rm | `fs.rm(path)` | Delete |
| symlink | `fs.symlink(target, link)` | Create symlink |
| chmod | `fs.chmod(path, mode)` | Change permissions |
| chown | `fs.chown(path, owner, group)` | Change ownership |
| compress | `fs.compress(src, dst)` | Archive |
| extract | `fs.extract(src, dst)` | Unarchive |

## API Endpoint

All filesystem ops go through: `POST /api/v1/fs/task` (create) and `GET /api/v1/fs/task/{id}` (poll).

## Tips

- Filesystem ops on compute resources (Polaris) access that resource's mounted filesystems
- Storage resources (Eagle, Home) provide dedicated storage access
- All tasks are non-blocking on the server side — poll via `.wait()` or `.refresh()`
- Set reasonable timeouts — large file ops may take minutes
