# Run Wenbin's transport model on lxplus

## Environment setup
### Install FASTJET 
Follow the instructions on the official website:\
`FASTJET3`:https://fastjet.fr/quickstart.html\
`FASTJET-contrib`:https://fastjet.hepforge.org/contrib/

### Install LHAPDF
```
wget https://lhapdf.hepforge.org/downloads/?f=LHAPDF-6.5.5.tar.gz -O LHAPDF-6.5.5.tar.gz
tar -xzvf LHAPDF-6.5.5.tar.gz
cd LHAPDF-6.5.5
mkdir -p /afs/cern.ch/user/x/xiaoyul/LHAPDF_Lib
./configure --prefix=/afs/cern.ch/user/x/xiaoyul/LHAPDF_Lib --disable-python
make -j8
make install
```
### Download PDF
```
wget http://lhapdfsets.web.cern.ch/lhapdfsets/current/NNPDF31_nnlo_as_0118.tar.gz
tar -xzvf NNPDF31_nnlo_as_0118.tar.gz
mv NNPDF31_nnlo_as_0118 /afs/cern.ch/user/x/xiaoyul/LHAPDF_Lib/share/LHAPDF/
```

### Install Pythia8 and compile with LHAPDF
```
wget https://pythia.org/download/pythia83/pythia8310.tgz
tar -xzvf pythia8310.tgz
cd pythia8310
./configure --prefix=/afs/cern.ch/user/x/xiaoyul/pythia8310_install --with-lhapdf6=/afs/cern.ch/user/x/xiaoyul/LHAPDF_Lib
make -j8
make install
```

## Produce samples on lxplus
### Clone the repository to your lxplus home directory: 
```
git clone git@github.com:liuxiaoyuyuyu/event0.git
``` 
### Tailor the codes to your own need:
- condor job submission (`event0/Cluster/lxplus/grid_Submit_transfer.py`)
    - EOS_SRC_DIR = "/eos/cms/store/group/phys_heavyions/xiaoyul/wenbin/event0"
    (I cloned the repo to /eos/, but later submit jobs from /afs/, you can do everything from /afs/) 
    - export PYTHIA8=/afs/cern.ch/user/x/xiaoyul/pythia8310_install\
    export LHAPDF_DATA_PATH=/afs/cern.ch/user/x/xiaoyul/LHAPDF_Lib/share/LHAPDF\
    export LD_LIBRARY_PATH=$PYTHIA8/lib:/afs/cern.ch/user/x/xiaoyul/LHAPDF_Lib/lib:$LD_LIBRARY_PATH
    - environment = "PYTHIA8=/afs/cern.ch/user/x/xiaoyul/pythia8310_install; LHAPDF_DATA_PATH=/afs/cern.ch/user/x/xiaoyul/LHAPDF_Lib/share/LHAPDF; LD_LIBRARY_PATH=/afs/cern.ch/user/x/xiaoyul/pythia8310_install/lib:/afs/cern.ch/user/x/xiaoyul/LHAPDF_Lib/lib:$$LD_LIBRARY_PATH; TERM=dumb"

- Output file path (`fastjet_hadron/fastjet_hadron_trackTree.cc`)
    - Default: `/eos/cms/store/group/phys_heavyions/xiaoyul/wenbin/sample/pp_parton_cascade_batch%d_%d.root`
    - Can be customized via command line argument or submission script

- Paths to Pythia and fastjet in Makefile
    - pythia_parton/Makefile
    - hadronization_urqmd/fragmentation/Makefile
    - fastjet_hadron/Makefile

### Modify the configuration if needed
- Spatial mode: `/event0/pythia_parton/mymain06.cc`
    - `int Spatial_mode = 0;` (accumulant method)
    - `int Spatial_mode = 1;` (free-streaming to the formation time)

    Note: use the accumulant method, set the spatial mode to 0!
- Partonic cross section: `/event0/ZPC/input.ampt`, line 23
    - 0.8 ($\sigma_p=24$ mb)
    - 2.265d0 ($\sigma_p=3$ mb);
    - 3.2032d0 ($\sigma_p=1.5$ mb); 
    - 1d4 ($\sigma_p=0$ mb)

- hFSI: `/event0/hadronization_urqmd/urqmd_code/urqmd/uqmd.burner`
    - `# cto 16 -1` (hFSI on)
    - `cto 16 -1` (hFSI off)

### Compile 
```
cd event0
cd pythia_parton
make clean  
make 
cd ../ZPC 
make clean 
make 
cd ../hadronization_urqmd/fragmentation 
make clean
make
cd ../urqmd_code 
make distclean 
FC=gfortran make
cd ./osc2u
chmod +x run_osc2u_safe.sh
cd ../../../fastjet_hadron
make clean 
make
```
### Submit condor jobs 
```bash
cd [dir_to_submit_jobs]
cp [.../event0/Cluster/lxplus/grid_Submit_transfer.py] .
mkdir logs
python3 grid_Submit_transfer.py N_jobs events_per_job batch_number [--tarball TARBALL] [--output-dir DIR] [--output-prefix PREFIX] [--seed-mode MODE]
```

- **Script and log names:** Derived from tarball name and batch number (third parameter): `tarball_base_batch_N` (e.g. `event0_0mb.tgz` and batch 0 → `NSC3_event0_0mb_batch_0.sh`, `Submit_event0_0mb_batch_0.sh`, `logs/out_event0_0mb_batch_0_$(Process).log`). Different tarballs or batch numbers give different names, so you can submit different settings at the same time without overwriting.

- **Seed mode** (`-s` / `--seed-mode`): `1` = random base + job id (default); `2` = deterministic hash(batch_number, job_id) so same batch+job gives the same seed; seeds are scattered (not sequential) to avoid RNG correlations.

**How seeds are set (per job):**  
Each job gets a **job id** = 0, 1, …, N_jobs−1 (Condor `$(Process)`).

- **Mode 1 (random):** At submit time the script draws a random base (0,10^9) and sets **effective_base** = random_base + batch_number × 400000. In the job:
  - **Pythia** seed = effective_base + job_id × **12345**
  - **HIJING** seed = effective_base + job_id × **54321**
  - **ZPC** seed = effective_base + job_id × **98765**  
  So each job has a different seed; resubmitting the same batch gives new random bases and thus new parton samples.

- **Mode 2 (deterministic, fixed partons):** Seeds depend only on (batch_number, job_id), no random draw. In the job:
  - **BASE** = (batch_number × **1000003** + job_id × **100003**) mod **2147483647**  (hash so seeds are scattered; 2147483647 = 2^31−1)
  - **Pythia** seed = BASE + 1
  - **HIJING** seed = (BASE + **100000007**) mod 2147483647 + 1
  - **ZPC** seed = (BASE + **200000007**) mod 2147483647 + 1  
  Same (batch_number, job_id) ⇒ same seeds ⇒ same Pythia partons; different (batch_number, job_id) ⇒ well-scattered seeds. Multipliers chosen so the sum fits in 32-bit for thousands of jobs.

**Usage example:**
```bash
# 2000 jobs, 0.1M events/job, batch 0; -t tarball; -d output dir; -p output prefix; -s seed mode. Script/log names: event0_0mb_batch_0 (from tarball + batch number).
python3 grid_Submit_transfer.py 2000 100000 0 -t event0_0mb.tgz -d /eos/cms/store/group/phys_heavyions/xiaoyul/wenbin/sample/wenbin_cuts/0mb/batch0 -p pp_parton_cascade_0mb -s 2
# Different tarball (e.g. event0_3mb.tgz) or batch number gives different script/log names, so you can run multiple settings at once.
```
`python3 grid_Submit_transfer.py --help` for full options.

**Inportant**: Please use grid_Submit_transfer.py for large-scale production. This script uses `transfer_input_files` instead of copying event0/ from EOS at runtime. Not all worker nodes have EOS mounted, so jobs may fail to access files if you use direct cp. In addition, heavy I/O to EOS is discouraged. Similarly, never directly copy from AFS, it will slow down the server and cause the AFS volume to be temporarily marked as “offline.” 

