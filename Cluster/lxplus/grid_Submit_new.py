#!/usr/bin/env python
# author: Wenbin Zhao (modified to use HTCondor transfer_input_files)
# email: wenbinzhao237@gmail.com

from subprocess import call, check_call
import sys
import random
import time
import os

EOS_SRC_DIR = "/eos/cms/store/group/phys_heavyions/xiaoyul/wenbin/event0"  # directory on EOS to ship
TARBALL_NAME = "event0.tgz"  # tarball we’ll create locally and transfer

def ensure_tarball(eos_src=EOS_SRC_DIR, tarball=TARBALL_NAME):
    """
    Create a tarball from the EOS source directory on the submit host.
    The submit host (AFS/lxplus) can see /eos; the worker nodes might not.
    """
    if not os.path.isdir(eos_src):
        raise RuntimeError(f"Source directory not found on submit host: {eos_src}")

    # Rebuild if missing or older than source (simple heuristic: rebuild if missing)
    if not os.path.exists(tarball):
        print(f"[prep] Creating tarball from {eos_src} -> {tarball}")
        # Pack the directory so the top-level folder inside tar is 'event0'
        # -C changes to the parent dir and tars the basename
        parent = os.path.dirname(eos_src.rstrip("/"))
        base = os.path.basename(eos_src.rstrip("/"))
        check_call(["tar", "-C", parent, "-czf", tarball, base])
    else:
        print(f"[prep] Using existing tarball: {tarball}")

def submit(njobs=1, nevent=10, batch_num=0):
    # Make sure logs/ exists
    if not os.path.exists('logs'):
        os.makedirs('logs')

    # Ensure tarball exists before we submit
    ensure_tarball()

    jobs = f'''#!/bin/bash
set -euo pipefail

echo "Host: $(hostname)"
echo "Date: $(date)"
echo "PWD : $PWD"
echo "Args: $@"
echo "=== Starting job execution ==="

export PYTHIA8=/afs/cern.ch/user/x/xiaoyul/pythia8310_install
export LHAPDF_DATA_PATH=/afs/cern.ch/user/x/xiaoyul/LHAPDF_Lib/share/LHAPDF
export LD_LIBRARY_PATH=$PYTHIA8/lib:/afs/cern.ch/user/x/xiaoyul/LHAPDF_Lib/lib:$LD_LIBRARY_PATH
export TERM=dumb
export COLUMNS=80
export LINES=24

# Get the job ID from Condor (0 to N-1)
JOB_ID=${{1:-0}}

pwd
echo "_CONDOR_SCRATCH_DIR=${{_CONDOR_SCRATCH_DIR:-}}"

# Create Playground directory if it doesn't exist
mkdir -p Playground

# Remove existing job directory if it exists
if [ -d "Playground/job-batch{batch_num}-$JOB_ID" ]; then
    echo "Removing existing job-batch{batch_num}-$JOB_ID directory..."
    rm -rf "Playground/job-batch{batch_num}-$JOB_ID"
fi

# Prepare job work area
mkdir -p "Playground/job-batch{batch_num}-$JOB_ID"

# Unpack shipped code (event0.tgz) into the job directory
if [ ! -f "{TARBALL_NAME}" ]; then
    echo "FATAL: missing {TARBALL_NAME} in working dir"; ls -la; exit 99
fi

tar -xzf {TARBALL_NAME} -C "Playground/job-batch{batch_num}-$JOB_ID"

cd "Playground/job-batch{batch_num}-$JOB_ID"

# If the tar contains a top-level 'event0' folder, flatten it
if [ -d event0 ]; then
    # Move contents of event0/* into current dir (ignore hidden dotfiles if none expected)
    shopt -s dotglob || true
    mv event0/* . || true
    rmdir event0 || true
    shopt -u dotglob || true
fi

# Generate the pythia parton
echo "=== Starting Pythia parton generation ==="
cd pythia_parton
./mymain06 {nevent} $(( {random.randint(0, 10**6)} + JOB_ID * 12345 ))
echo "=== Pythia parton generation completed ==="
cd ../

# ZPC for parton cascade
echo "=== Starting ZPC parton cascade ==="
cd ZPC
mkdir -p ana
ln -sf ../pythia_parton/parton_info.dat ./

# Generate job-specific seeds for ZPC
HIJING_SEED=$(( {random.randint(0, 10**6)} + JOB_ID * 54321 ))
ZPC_SEED=$(( {random.randint(0, 10**6)} + JOB_ID * 98765 ))

# Create custom input.ampt with job-specific seeds and event number
sed "s/^0[[:space:]]*![[:space:]]*ihjsed/11      ! ihjsed/" input.ampt | \\
sed "s/^53153515[[:space:]]*![[:space:]]*random seed for HIJING/$HIJING_SEED    ! random seed for HIJING/" | \\
sed "s/^8[[:space:]]*![[:space:]]*random seed for parton cascade/$ZPC_SEED      ! random seed for parton cascade/" | \\
sed "s/^10[[:space:]]*![[:space:]]*NEVNT/{nevent}            ! NEVNT/" > input_custom.ampt

cp input_custom.ampt input.ampt
echo "#  ZPC started at $(date)" > start.time
echo $HIJING_SEED | ./exec > nohup.out
uname -n >> nohup.out
cat start.time >> nohup.out
rm -f start.time
echo "#  ZPC Program finished at $(date)" >> nohup.out
echo "=== ZPC parton cascade completed ==="

cd ../

# fragmentation and urqmd
echo "=== Starting fragmentation and UrQMD ==="
cd hadronization_urqmd
cd fragmentation
ln -sf ../../ZPC/ana/zpc.dat ./
./main_string_fragmentation {nevent}

cd ../urqmd_code
    # script to run urqmd
    cd osc2u
    ln -sf ../../fragmentation/hadrons_frag1.dat ./
    ./osc2u.e < hadrons_frag1.dat > run.log
    rm -f ../../fragmentation/hadrons_frag1.dat
    mv fort.14 ../urqmd/OSCAR.input
    cd ../urqmd
    ./runqmd.sh > run.log
    rm -f OSCAR.input
    rm -f run.log
    cd ..
cd ../
cd ../

# jet finding of final hadrons
echo "=== Starting FastJet analysis ==="
cd fastjet_hadron
ln -sf ../hadronization_urqmd/urqmd_code/urqmd/particle_list.dat ./
ln -sf ../pythia_parton/parton_info.dat ./
ln -sf ../hadronization_urqmd/fragmentation/hadrons_frag_full.dat ./
ln -sf ../ZPC/ana/zpc.dat ./
ln -sf ../ZPC/ana/zpc.res ./
./fastjet_hadron_trackTree {nevent} $JOB_ID {batch_num}
echo "=== FastJet analysis completed ==="
cd ../

# Clean up heavy directories to reduce output size
echo "=== Cleaning up and finishing job ==="
rm -rf fastjet_hadron hadronization_urqmd pythia_parton ZPC
cd ../
rm -rf "job-batch{batch_num}-$JOB_ID"
cd ../
echo "=== Job completed successfully ==="
'''

    job_name = f"NSC3_batch{batch_num}.sh"
    with open(job_name, 'w') as fout:
        fout.write(jobs)
    os.chmod(job_name, 0o755)

    condor_submit = f'''universe                = vanilla
executable              = {job_name}
arguments               = $(Process)
# Transfer the executable and inputs to the worker
should_transfer_files   = YES
when_to_transfer_output = ON_EXIT_OR_EVICT
# Ship the tarball containing your code/data
transfer_input_files    = {TARBALL_NAME}

# Environment (kept from your original)
environment = "PYTHIA8=/afs/cern.ch/user/x/xiaoyul/pythia8310_install; LHAPDF_DATA_PATH=/afs/cern.ch/user/x/xiaoyul/LHAPDF_Lib/share/LHAPDF; LD_LIBRARY_PATH=/afs/cern.ch/user/x/xiaoyul/pythia8310_install/lib:/afs/cern.ch/user/x/xiaoyul/LHAPDF_Lib/lib:$$LD_LIBRARY_PATH"

# Logs stay on the submit host (AFS)
output                  = logs/out_batch{batch_num}_$(Process).log
error                   = logs/err_batch{batch_num}_$(Process).log
log                     = logs/condor_batch{batch_num}.log

+MaxRuntime             = 200000
queue {njobs}
'''
    job_name2 = f"Submit_batch{batch_num}.sh"
    with open(job_name2, 'w') as fout:
        fout.write(condor_submit)

    print(f"Submitting batch {batch_num}: {njobs} jobs with {nevent} events each")
    print(f"Condor submit file: {job_name2}")
    print(f"Bash script: {job_name}")

    # Submit
    call(['condor_submit', job_name2])

if __name__=='__main__':
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
