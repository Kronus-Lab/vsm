{ pkgs, lib, ... }:
{
  languages = {
    python = {
      enable = true;
      version = "3.13";
      venv.enable = true;
    };
    javascript.enable = true;
  };

  packages = [
    pkgs.ansible
    pkgs.nodejs_22
    pkgs.terraform
  ];

  enterShell = lib.concatStringsSep " && " [
    "pip install -r requirements.txt"
    "pip install -r requirements-dev.txt"
    "npm install"
    "docker buildx build -t kr0nus/vsm:devel ."
  ];

}