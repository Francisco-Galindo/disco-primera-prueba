{ pkgs ? import <nixpkgs> {} }:

pkgs.mkShell {
  buildInputs = [
    pkgs.python312Packages.simpy
  ];
  packages = with pkgs; [
    gnuplot
    python312Packages.simpy
  ];
}
