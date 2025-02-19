set terminal png
set output 'data.png'

N = system("awk -F '\t' 'NR==1{print NF}' data.dat")
plot for [i=2:N] "data.dat" using 1:i ps 0.25
