#!/usr/bin/env python
#author: Wenbin Zhao
#email: wenbinzhao237@gmail.com

from subprocess import call
import sys
import random
import time
import os

def submit(njobs=1, nevent=10, batch_num=0):
    jobs = '''#!/bin/bash

hostname
date

export PYTHIA8=/afs/cern.ch/user/x/xiaoyul/pythia8310_install
export LHAPDF_DATA_PATH=/afs/cern.ch/user/x/xiaoyul/LHAPDF_Lib/share/LHAPDF
export LD_LIBRARY_PATH=$PYTHIA8/lib:/afs/cern.ch/user/x/xiaoyul/LHAPDF_Lib/lib:$LD_LIBRARY_PATH

# Get the job ID from Condor (0 to N-1)
JOB_ID=$1

pwd 
echo $_CONDOR_SCRATCH_DIR

# Create Playground directory if it doesn't exist
if [ ! -d "Playground" ]; then
    mkdir -p Playground
fi

# Remove existing job directory if it exists
if [ -d "Playground/job-batch{batch_num}-$JOB_ID" ]; then
    echo "Removing existing job-batch{batch_num}-$JOB_ID directory..."
    rm -rf Playground/job-batch{batch_num}-$JOB_ID
fi

cp -r /eos/cms/store/group/phys_heavyions/xiaoyul/wenbin/event0 Playground/job-batch{batch_num}-$JOB_ID
cd Playground/job-batch{batch_num}-$JOB_ID

# Generate the pythia parton
cd pythia_parton
./mymain06 {nevent} $(({random_seed} + $JOB_ID * 12345))
cd ../

# ZPC for parton cascade
cd ZPC
mkdir -p ana
ln -sf ../pythia_parton/parton_info.dat ./

# Generate job-specific seeds for ZPC
HIJING_SEED=$(({random_seed} + $JOB_ID * 54321))
ZPC_SEED=$(({random_seed} + $JOB_ID * 98765))

# Create custom input.ampt with job-specific seeds and event number
sed "s/^0[[:space:]]*![[:space:]]*ihjsed/11      ! ihjsed/" input.ampt | \\
sed "s/^53153515[[:space:]]*![[:space:]]*random seed for HIJING/$HIJING_SEED    ! random seed for HIJING/" | \\
sed "s/^8[[:space:]]*![[:space:]]*random seed for parton cascade/$ZPC_SEED      ! random seed for parton cascade/" | \\
sed "s/^10[[:space:]]*![[:space:]]*NEVNT/{nevent}            ! NEVNT/" > input_custom.ampt

# Replace the original input.ampt with our custom one
cp input_custom.ampt input.ampt
echo "#  ZPC started at " `date` > start.time
echo $HIJING_SEED | ./exec > nohup.out
uname -n >> nohup.out
cat start.time >> nohup.out
rm -f start.time
echo "#  ZPC Program finished at " `date` >> nohup.out

cd ../

# fragmentation and urqmd
cd hadronization_urqmd
cd fragmentation
ln -sf ../../ZPC/ana/zpc.dat ./
./main_string_fragmentation {nevent}

cd ../urqmd_code
    # script to run urqmd
    cd osc2u
    ln -sf ../../fragmentation/hadrons_frag1.dat ./
    ./osc2u.e < hadrons_frag1.dat > run.log
    rm -r ../../fragmentation/hadrons_frag1.dat
    mv fort.14 ../urqmd/OSCAR.input
    cd ../urqmd
    ./runqmd.sh > run.log
    rm -fr OSCAR.input
    rm -rf run.log
    cd ..
cd ../
cd ../

# jet finding of final hadrons
cd fastjet_hadron
ln -sf ../hadronization_urqmd/urqmd_code/urqmd/particle_list.dat ./
ln -sf ../pythia_parton/parton_info.dat ./
ln -sf ../hadronization_urqmd/fragmentation/hadrons_frag_full.dat ./
ln -sf ../ZPC/ana/zpc.dat ./
ln -sf ../ZPC/ana/zpc.res ./
./fastjet_hadron_trackTree {nevent} $JOB_ID {batch_num}
cd ../

# Clean up
rm -r fastjet_hadron
rm -r hadronization_urqmd
rm -r pythia_parton
rm -r ZPC
cd ../
rm -rf job-batch{batch_num}-$JOB_ID
cd ../
'''.format(nevent=nevent, random_seed=random.randint(0, 10**6), batch_num=batch_num)

    job_name = f"NSC3_batch{batch_num}.sh"
    with open(job_name, 'w') as fout:
        fout.write(jobs)

    condor_submit = '''universe        = vanilla
environment = "PYTHIA8=/afs/cern.ch/user/x/xiaoyul/pythia8310_install; LHAPDF_DATA_PATH=/afs/cern.ch/user/x/xiaoyul/LHAPDF_Lib/share/LHAPDF; LD_LIBRARY_PATH=/afs/cern.ch/user/x/xiaoyul/pythia8310_install/lib:/afs/cern.ch/user/x/xiaoyul/LHAPDF_Lib/lib:$$LD_LIBRARY_PATH"
executable      = {job_name}
arguments       = $(Process)
output          = logs/out_batch{batch_num}_$(Process).log
error           = logs/err_batch{batch_num}_$(Process).log
log             = logs/condor_batch{batch_num}.log
+MaxRuntime =40000
queue {njobs}
    '''.format(job_name=job_name, njobs=njobs, batch_num=batch_num)
    
    job_name2 = f"Submit_batch{batch_num}.sh"
    with open(job_name2, 'w') as fout:
        fout.write(condor_submit)
    
    # Create logs directory if it doesn't exist
    if not os.path.exists('logs'):
        os.makedirs('logs')
    
    call(['condor_submit', job_name2])
    
    print(f"Submitted batch {batch_num}: {njobs} jobs with {nevent} events each")
    print(f"Condor submit file: {job_name2}")
    print(f"Bash script: {job_name}")

if __name__=='__main__':
    import sys
    if len(sys.argv) != 4:
        print("Usage: python3 grid_Submit.py <N_jobs> <events_per_job> <batch_number>")
        print("Example: python3 grid_Submit.py 100 50000 0")
        print("Example: python3 grid_Submit.py 100 50000 1")
        sys.exit(1)
    
    njobs = int(sys.argv[1])      # Number of jobs (0 to N-1)
    nevent = int(sys.argv[2])     # Events per job
    batch_num = int(sys.argv[3])  # Batch number for unique output names
    
    print(f"Submitting batch {batch_num}: {njobs} jobs with {nevent} events each")
    submit(njobs, nevent, batch_num)