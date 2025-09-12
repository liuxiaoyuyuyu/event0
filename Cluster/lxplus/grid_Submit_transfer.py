#!/usr/bin/env python
#author: Wenbin Zhao (modified to use HTCondor transfer_input_files)
#email: wenbinzhao237@gmail.com

from subprocess import call, check_call
import sys
import random
import time
import os

EOS_SRC_DIR = "/eos/cms/store/group/phys_heavyions/xiaoyul/wenbin/event0"  # directory on EOS to ship
TARBALL_NAME = "event0.tgz"  # tarball we'll create locally and transfer

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

    # Generate a random base seed for this batch
    random_base_seed = random.randint(0, 10**6)

    # Ensure tarball exists before we submit
    ensure_tarball()

    jobs = '''#!/bin/bash
set -euo pipefail

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
./mymain06 {nevent} $(({random_base_seed} + $JOB_ID * 12345))
echo "Checking if parton_info.dat was created:"
ls -la parton_info.dat
echo "First few lines of parton_info.dat:"
head -5 parton_info.dat
echo "=== Pythia parton generation completed ==="
cd ../

# ZPC for parton cascade
echo "=== Starting ZPC parton cascade ==="
cd ZPC
echo "Current directory: $(pwd)"
mkdir -p ana
ln -sf ../pythia_parton/parton_info.dat ./
echo "Created ana directory and linked parton_info.dat"

# Generate job-specific seeds for ZPC
HIJING_SEED=$(({random_base_seed} + $JOB_ID * 54321))
ZPC_SEED=$(({random_base_seed} + $JOB_ID * 98765))
echo "Generated seeds: HIJING=$HIJING_SEED, ZPC=$ZPC_SEED"

# Create custom input.ampt with job-specific seeds and event number
echo "Creating custom input.ampt..."
sed "s/^0[[:space:]]*![[:space:]]*ihjsed/11      ! ihjsed/" input.ampt | \\
sed "s/^53153515[[:space:]]*![[:space:]]*random seed for HIJING/$HIJING_SEED    ! random seed for HIJING/" | \\
sed "s/^8[[:space:]]*![[:space:]]*random seed for parton cascade/$ZPC_SEED      ! random seed for parton cascade/" | \\
sed "s/^10[[:space:]]*![[:space:]]*NEVNT/{nevent}            ! NEVNT/" > input_custom.ampt

# Replace the original input.ampt with our custom one
cp input_custom.ampt input.ampt
echo "Copied custom input.ampt"
echo "Checking input.ampt content:"
head -10 input.ampt
echo "Checking if exec is executable:"
ls -la exec
echo "Starting ZPC exec with seed: $HIJING_SEED"
echo "Contents of nseed_runtime before exec:"
cat nseed_runtime
echo "Running ZPC exec wrapper..."
echo $HIJING_SEED | ./exec
echo "ZPC exec completed"
echo "Checking ZPC output files:"
ls -la ana/
echo "First few lines of zpc.dat:"
head -5 ana/zpc.dat
echo "First few lines of zpc.res:"
head -5 ana/zpc.res
echo "=== ZPC parton cascade completed ==="

cd ../

# fragmentation and urqmd
echo "=== Starting fragmentation and UrQMD ==="
cd hadronization_urqmd
cd fragmentation
echo "Current directory: $(pwd)"
ln -sf ../../ZPC/ana/zpc.dat ./
echo "Linked zpc.dat, starting fragmentation..."
./main_string_fragmentation {nevent}
echo "Fragmentation completed"
echo "Checking fragmentation output files:"
ls -la *.dat
echo "First few lines of hadrons_frag1.dat:"
head -5 hadrons_frag1.dat
echo "First few lines of hadrons_frag_full.dat:"
head -5 hadrons_frag_full.dat

cd ../urqmd_code
    # script to run urqmd
    echo "Starting UrQMD processing..."
    cd osc2u
    echo "Current directory: $(pwd)"
    ln -sf ../../fragmentation/hadrons_frag1.dat ./
    echo "Linked hadrons_frag1.dat, running osc2u..."
    ./osc2u.e < hadrons_frag1.dat > run.log
    echo "osc2u completed"
    rm -r ../../fragmentation/hadrons_frag1.dat
    mv fort.14 ../urqmd/OSCAR.input
    cd ../urqmd
echo "Running UrQMD..."
./runqmd.sh > run.log
echo "UrQMD completed"
echo "Checking UrQMD output files:"
ls -la *.dat
echo "First few lines of particle_list.dat:"
head -5 particle_list.dat
rm -fr OSCAR.input
rm -rf run.log
cd ..
cd ../
cd ../
echo "=== Fragmentation and UrQMD completed ==="

# jet finding of final hadrons
echo "=== Starting FastJet analysis ==="
cd fastjet_hadron
echo "Current directory: $(pwd)"
ln -sf ../hadronization_urqmd/urqmd_code/urqmd/particle_list.dat ./
ln -sf ../pythia_parton/parton_info.dat ./
ln -sf ../hadronization_urqmd/fragmentation/hadrons_frag_full.dat ./
ln -sf ../ZPC/ana/zpc.dat ./
ln -sf ../ZPC/ana/zpc.res ./
echo "Linked all input files, starting FastJet analysis..."
echo "Checking input files for FastJet:"
ls -la *.dat
echo "First few lines of particle_list.dat:"
head -3 particle_list.dat
echo "First few lines of parton_info.dat:"
head -3 parton_info.dat
./fastjet_hadron_trackTree {nevent} $JOB_ID {batch_num}
echo "FastJet analysis completed"
echo "Checking if ROOT output was created:"
ls -la *.root
cd ../
echo "=== FastJet analysis completed ==="

# Clean up
rm -r fastjet_hadron
rm -r hadronization_urqmd
rm -r pythia_parton
rm -r ZPC
cd ../
rm -rf job-batch{batch_num}-$JOB_ID
cd ../
'''.format(nevent=nevent, random_base_seed=random_base_seed, batch_num=batch_num, TARBALL_NAME=TARBALL_NAME)

    job_name = f"NSC3_batch{batch_num}.sh"
    with open(job_name, 'w') as fout:
        fout.write(jobs)
    os.chmod(job_name, 0o755)

    condor_submit = '''universe                = vanilla
executable              = {job_name}
arguments               = $(Process)
# Transfer the executable and inputs to the worker
should_transfer_files   = YES
when_to_transfer_output = ON_EXIT_OR_EVICT
# Ship the tarball containing your code/data
transfer_input_files    = {TARBALL_NAME}

# Environment (kept from your original + terminal fix)
environment = "PYTHIA8=/afs/cern.ch/user/x/xiaoyul/pythia8310_install; LHAPDF_DATA_PATH=/afs/cern.ch/user/x/xiaoyul/LHAPDF_Lib/share/LHAPDF; LD_LIBRARY_PATH=/afs/cern.ch/user/x/xiaoyul/pythia8310_install/lib:/afs/cern.ch/user/x/xiaoyul/LHAPDF_Lib/lib:$$LD_LIBRARY_PATH; TERM=dumb"

# Logs stay on the submit host (AFS)
output                  = logs/out_batch{batch_num}_$(Process).log
error                   = logs/err_batch{batch_num}_$(Process).log
log                     = logs/condor_batch{batch_num}.log

+MaxRuntime             = 40000
queue {njobs}
'''.format(job_name=job_name, TARBALL_NAME=TARBALL_NAME, batch_num=batch_num, njobs=njobs)
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
        print("Usage: python3 grid_Submit_transfer.py <N_jobs> <events_per_job> <batch_number>")
        print("Example: python3 grid_Submit_transfer.py 100 50000 0")
        print("Example: python3 grid_Submit_transfer.py 100 50000 1")
        sys.exit(1)

    njobs = int(sys.argv[1])      # Number of jobs (0 to N-1)
    nevent = int(sys.argv[2])     # Events per job
    batch_num = int(sys.argv[3])  # Batch number for unique output names

    print(f"Submitting batch {batch_num}: {njobs} jobs with {nevent} events each")
    submit(njobs, nevent, batch_num)
