# -*- coding: UTF-8 -*-

from sak import ctx
from sakonto import owl, Sak
from sakplugin import SakPlugin
#from sakcmd import SakCmd, SakArg, SakProperty

import git
from git import Repo

import re
from pathlib import Path
import subprocess

from typing import Optional


class SakGit(SakPlugin):
    'Git commands'
    def __init__(self, name) -> None:
        super(SakGit, self).__init__('git')

    def onto_declare(self, local_onto):
        class GitRepo(Sak):
            pass

        class GitRemote(Sak):
            pass

        class GitCommit(Sak):
            pass

        class GitCommitAuthor(Sak):
            pass

    def onto_impl(self, local_onto):
        class GitRepo(Sak):
            __repo = None

            @property
            def repo(self):
                if self.__repo is None:
                    try:
                        self.__repo = Repo(self.has_path, search_parent_directories=True)
                    except git.exc.InvalidGitRepositoryError as e:
                        raise Exception(f'No git repository found in {self.path}')
                return self.__repo

            @property
            def path(self):
                return Path(self.has_path)

            def get_hash(self, bname: str = 'HEAD') -> Optional[str]:
                '''Get the current commit hash'''
                self.repo
                try:
                    cmd = ['git', 'log', '-1', bname]
                    p = subprocess.run(cmd,
                                       check=True,
                                       stdout=subprocess.PIPE,
                                       stderr=subprocess.DEVNULL,
                                       cwd=self.path)
                    text = p.stdout.strip().decode("utf-8")
                    r: List[str] = re.findall('commit ([a-f0-9]+)', text)
                    if r:
                        return r[0]
                    else:
                        return None
                except:
                    return None

            def sync(self):
                remote_url = self.repo.remote().url

                remote_name = remote_url

                remote = GitRemote(remote_name)
                remote.has_git_remote_url = remote_url

                self.has_remote = []
                self.has_remote.append(remote)

        class GitRemote(Sak):
            pass

        class GitCommit(Sak):
            pass

        class GitCommitAuthor(Sak):
            pass

        # Properties
        class has_commits(GitRepo >> GitCommit):
            pass

        # TODO(witt): Could be a class for Person.
        class has_commit_author(GitCommit >> str, owl.FunctionalProperty):
            pass

        class has_remote(GitRepo >> GitRemote):
            pass

        class has_path(GitRepo >> str, owl.FunctionalProperty):
            pass

        class has_git_remote_url(GitRemote >> str, owl.FunctionalProperty):
            pass

    @property
    def repo(self, path=None):
        '''Git object for current path'''
        # TODO(witt): SakProperty is not expanded automatically, if it gives some exception while expanding the tree I should not add it.
        #try:
        if path is None:
            path = str(ctx.current_dir)

        repo = self.get_ontology().GitRepo(path)
        repo.has_path = path

        return repo
