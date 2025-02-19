set terminal png
set output 'fig09.png'

N = system("awk -F '\t' 'NR==1{print NF}' fig09.dat")
plot for [i=2:N] "fig09.dat" using 1:i ps 0.25
