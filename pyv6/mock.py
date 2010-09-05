O_RDONLY  = 0x000
O_WRONLY  = 0x001
O_RDWR    = 0x002
O_CREATE  = 0x200

T_DIR  = 1   # Directory
T_FILE = 2   # File
T_DEV  = 3   # Special device


import sys
import pickle


class Exit(Exception):
    pass


class File(object):
    def __init__(self, contents):
        self.contents = contents
        self.type = T_FILE
        self.dev = 1
        self.ino = 123
        self.nlink = 0
    
    @property
    def size(self):
        return len(self.contents)


class ModuleFile(File):
    def __init__(self, module_name):
        main = __import__(module_name, fromlist=["main"]).main
        contents = pickle.dumps(main)
        super(ModuleFile, self).__init__(contents)

class Dir(object):
    def __init__(self, contents):
        self.type = T_DIR
        self.dev = 1
        self.ino = 234
        self.nlink = 0
        self.contents = contents
    
    @property
    def size(self):
        return len(self.contents)


class MockFileSystem:
    
    def __init__(self):
        self.files = {}
        self.files["/foo"] = File("contents of foo!\n")
        self.files["/biz"] = Dir("123456alpha         987654beta          ")
        self.files["/biz/alpha"] = File("contents of alpha!\n")
        self.files["/biz/beta"] = File("contents of beta!\n")
        self.fds = {}
    
    def open(self, path, mode):
        if path not in self.files:
            if mode & O_CREATE:
                self.files[path] = File("")
            else:
                return -1
        next_fd = len(self.fds) + 3
        self.fds[next_fd] = (path, mode, 0, self.files[path])
        return next_fd
    
    def read(self, fd, max_size):
        if fd == 0:
            buf = sys.stdin.read(max_size)
            return len(buf), buf
        elif fd == 1:
            sys.stdout.write(buf[:length])
        elif fd == 2:
            assert False
        else:
            path, mode, ptr, f = self.fds[fd]
            if ptr >= len(f.contents):
                return 0, "" # EOF
            end = min(len(f.contents), ptr + max_size)
            buf = f.contents[ptr:end]
            self.fds[fd] = (path, mode, end, f)
            return len(buf), buf
    
    def write(self, fd, buf, length):
        if fd == 0:
            assert False
        elif fd == 1:
            sys.stdout.write(buf[:length])
        elif fd == 2:
            sys.stderr.write(buf[:length])
        else:
            path, mode, end, f = self.fds[fd]
            if mode & O_WRONLY or mode & O_RDWR:
                f.contents += buf[:length] # @@@
                return length # @@@
            else:
                assert False
    
    def close(self, fd):
        del self.fds[fd]
    
    def fstat(self, fd):
        class Stat: pass
        path, mode, ptr, f = self.fds[fd]
        s = Stat()
        s.type = f.type     # Type of file
        s.dev = f.dev       # Device number
        s.ino = f.ino       # Inode number on device
        s.nlink = f.nlink   # Number of links to file
        s.size = f.size     # Size of file in bytes
        return 0, s
    
    def unlink(self, path):
        try:
            del self.files[path]
            return 0
        except KeyError:
            return -1


MockFS = MockFileSystem()

def mock_open(path, mode):
    return MockFS.open(path, mode)

def mock_read(fd, max_size):
    return MockFS.read(fd, max_size)

def mock_write(fd, buf, length):
    return MockFS.write(fd, buf, length)

def mock_close(fd):
    return MockFS.close(fd)

def mock_fstat(fd):
    return MockFS.fstat(fd)

def mock_unlink(path):
    return MockFS.unlink(path)

def mock_exec(path, argv):
    try:
        fd = mock_open(path, O_RDONLY)
        dummy, contents = mock_read(fd, 1000000)
        mock_close(fd)
        main = pickle.loads(contents)
        main(len(argv), argv)
    except Exit:
        return 0
    
    # if we get here we *should* have seen an Exit but didn't
    return -1
