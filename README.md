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
    - TFile * fout = TFile::Open( Form("/eos/cms/store/group/phys_heavyions/xiaoyul/wenbin/sample/pp_parton_cascade_batch%d_%d.root", batch_number, job_id) ,"recreate");

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
make clean 
FC=gfortran make 
cd ../../fastjet_hadron
make clean 
make
```
### Submit condor jobs 
```
cd [dir_to_submit_jobs]
cp [.../event0/Cluster/lxplus/grid_Submit.py] .
mkdir logs
python3 grid_Submit_transfer.py [N_jobs] [N_events_per_job] [batch] 
```
e.g.\
`python3 grid_Submit_transfer.py 1 10 0` (test)\
`python3 grid_Submit_transfer.py 2000 100000 1`

**Inportant**: Please use grid_Submit_transfer.py for large-scale production. This script uses `transfer_input_files` instead of copying event0/ from EOS at runtime. Not all worker nodes have EOS mounted, so jobs may fail to access files if you use direct cp. In addition, heavy I/O to EOS is discouraged. Similarly, never directly copy from AFS, it will slow down the server and cause the AFS volume to be temporarily marked as “offline.” 

