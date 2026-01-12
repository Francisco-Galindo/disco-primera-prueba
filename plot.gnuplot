set terminal png
set output 'dc-2.png'

N = system("awk -F '\t' 'NR==1{print NF}' dc.dat")
set logscale y  
# set logscale x
set xrange [0.02:*]
set yrange [10:*]
plot for [i=2:N] "dc.dat" using 1:i ps 0.25 with linespoints
