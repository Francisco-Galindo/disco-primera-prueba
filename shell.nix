{ pkgs ? import <nixpkgs> {} }:

pkgs.mkShell {
  buildInputs = [
    pkgs.python312Packages.simpy
  ];
  packages = with pkgs; [
    gnuplot
    python312Packages.matplotlib
    python312Packages.simpy
  ];
}
