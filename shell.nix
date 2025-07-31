{
  pkgs ? import <nixpkgs> { },
}:

let
  pythonPackages = pkgs.python311Packages; # Change to Python 3.10
in
pkgs.mkShell rec {
  name = "concatenate-files";

  buildInputs = with pkgs; [
    gcc # Required for crates needing C compilers
    pkg-config # Helps locate libraries like OpenSSL
    openssl # OpenSSL library for crates like openssl-sys
    git
    git-crypt
    stdenv.cc.cc.lib
    stdenv.cc.cc # jupyter lab needs
    zlib
    zlib.out
    pythonPackages.python
    pythonPackages.pyzmq
    pythonPackages.pip
    pythonPackages.ruff
    pythonPackages.click
    pythonPackages.pathspec
    pythonPackages.tqdm
    pythonPackages.pytest
    pre-commit
    uv
  ];

  postVenvCreation = ''
    unset SOURCE_DATE_EPOCH
  '';

  pre-commit = pkgs.pre-commit;

  postShellHook = ''
    unset SOURCE_DATE_EPOCH

    export PKG_CONFIG_PATH="${pkgs.openssl.dev}/lib/pkgconfig:$PKG_CONFIG_PATH"

    echo "Environment setup complete. UV and hatchling are available."
    export LD_LIBRARY_PATH=${pkgs.zlib}/lib:$LD_LIBRARY_PATH
  '';
}
