LIST1=(0 40 50)        # 11 elements
# LIST1=(0 20 30)        # 11 elements
LIST2=(0 1 5 10 25 50 75 90 99)   # 9 elements
# LIST1=(0 2 5 10 20 50)        # 11 elements
# LIST2=(0 5)   # 9 elements
TRIALS=30
for i in $(seq 2); do
    for j in $(seq 8); do
	echo "---------------------------------------"
	echo "RUNNING" ${LIST1[$i]} ${LIST2[$j]} $TRIALS
	python3 graph.py ${LIST1[$i]} ${LIST2[$j]} $TRIALS
    done
done
