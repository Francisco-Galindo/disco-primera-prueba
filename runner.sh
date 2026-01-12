LIST1=(0 2 3 5 10 15 20 50 100)        # 8 elements
LIST2=(0 1 2 5 10 15 20 50 75 90 99)   # 10 elements
for i in $(seq 8); do
    for j in $(seq 10); do
	echo "---------------------------------------"
	echo "RUNNING" ${LIST1[$i]} ${LIST2[$j]}
	python3 graph.py ${LIST1[$i]} ${LIST2[$j]}
    done
done
