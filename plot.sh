#!/usr/bin/env bash

gnuplot << EOF
set term png
set output "$2"
set xlabel "Slot"
set ylabel "Discovery proportion"
plot for[col=2:$(awk -F' ' '{print NF}' $1 | head -n 1)] "$1" using 1:col title columnheader(col) with lines
EOF
