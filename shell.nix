{ pkgs ? import <nixpkgs> {} }:

pkgs.mkShell {
  buildInputs = [
    pkgs.python312Packages.sympy
  ];
  packages = with pkgs; [
    gnuplot
  ];
}
