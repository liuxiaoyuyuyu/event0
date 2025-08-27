#include "fastjet/ClusterSequence.hh"
#include "fastjet/PseudoJet.hh"
#include "fastjet/contrib/SoftDrop.hh"
#include "Pythia8/Pythia.h"
#include "TMath.h"
#include "TTree.h"
#include "TBranch.h"
#include "TFile.h"
#include "TSystem.h"
#include "TInterpreter.h"

//standard cpp libraries
#include <vector>
#include <ctime>
#include <iostream>
#include <fstream>
#include <string>

//namespaces
using namespace std;
using namespace Pythia8;
using namespace fastjet;
Pythia pythia;
Pythia8::ParticleData &particleData = pythia.particleData;

int main(int argv, char* argc[])
{
    gInterpreter->GenerateDictionary("vector<vector<float> >", "vector");
    gInterpreter->GenerateDictionary("vector<vector<int> >", "vector");

    int Nevent = atoi(argc[1]);
    int jobnumber = atoi(argc[2]);
    // selection for final particles which are used to reconstruct jet
    double absetamax = 2.4;
    // parameter setting
    const double z_cut = 0.1;
    const double R_jet = 0.8; // CMS cut, CMS PAS HIN-21-013
    fastjet::contrib::SoftDrop softdrop(1, z_cut, R_jet);
    softdrop.set_reclustering(false, 0);

    const double jet_ptmin = 500.0;
    double jet_absetamax = 1.6;
    vector<fastjet::PseudoJet> input_particles;
    char inputfile[128];
    sprintf(inputfile, "particle_list.dat");
    FILE* infile;
    infile = fopen(inputfile,"r");
    char stemp1[100];
    char** stemp2;
    int total_number_of_particles, pid, event_id, int_temp, status;
    double px, py, pz, energy, mass, dummpx, dummpy, dummpz, dummpt, weight;
    int event_loop_flag = 1;
    int count_event_number = 0;
    
    //Save the parton info

    ifstream inputFile_p("parton_info.dat");
    if (!inputFile_p.is_open()) {
        cerr << "Error opening parton_info.dat!" << endl;
        return 1;
    }
    string line;
    string line2;
    getline(inputFile_p, line); // Read and ignore the first line

    ifstream inputFile_h("hadrons_frag_full.dat");
    if (!inputFile_h.is_open()) {
        cerr << "Error opening hadrons_frag_full.dat!" << endl;
        return 1;
    }
    string lineh;

    ifstream inputFile_zpc("zpc.dat");
    if (!inputFile_zpc.is_open()) {
        cerr << "Error opening zpc.dat!" << endl;
        return 1;
    }
    string lineZpc;

    int par_pdgid;
    double par_px, par_py, par_pz, par_e, par_x, par_y, par_z, par_t, mid1, mid2;

    // parton stuff - before ZPC
    std::vector<int> parton_pid;
    std::vector<float> parton_px;
    std::vector<float> parton_py;
    std::vector<float> parton_pz;
    std::vector<float> parton_e;
    std::vector<float> parton_x;
    std::vector<float> parton_y;
    std::vector<float> parton_z;
    std::vector<float> parton_t;
    std::vector<int> parton_color1;
    std::vector<int> parton_color2;

    // parton stuff - after ZPC
    std::vector<int> parton_pid_after_zpc;
    std::vector<float> parton_px_after_zpc;
    std::vector<float> parton_py_after_zpc;
    std::vector<float> parton_pz_after_zpc;
    std::vector<float> parton_e_after_zpc;
    std::vector<float> parton_x_after_zpc;
    std::vector<float> parton_y_after_zpc;
    std::vector<float> parton_z_after_zpc;
    std::vector<float> parton_t_after_zpc;
    std::vector<int> parton_color1_after_zpc;
    std::vector<int> parton_color2_after_zpc;

    std::vector<float> genpx;
    std::vector<float> genpy;
    std::vector<float> genpz;
    std::vector<float> genm;
    std::vector<int> genpid;
    std::vector<int> genchg;

    // jet stuff
    std::vector<float> genJetPt;
    std::vector<float> genJetEta;
    std::vector<float> genJetPhi;
    std::vector<int> genJetChargedMultiplicity;
    std::vector<double > Zgs;
    std::vector<double > Rgs;
    std::vector<double > ZgTgBs;
    std::vector<double > SDJetMass;
    std::vector<std::vector<int>> gendau_chg;
    std::vector<std::vector<int>> gendau_pid;
    std::vector<std::vector<float>> gendau_pt;
    std::vector<std::vector<float>> gendau_eta;
    std::vector<std::vector<float>> gendau_phi;

    TTree *trackTree = new TTree("trackTree", "v1");

    // Before ZPC branches
    trackTree->Branch("par_pdgid", &parton_pid);
    trackTree->Branch("par_px", &parton_px);
    trackTree->Branch("par_py", &parton_py);
    trackTree->Branch("par_pz", &parton_pz);
    trackTree->Branch("par_e", &parton_e);
    trackTree->Branch("par_x", &parton_x);
    trackTree->Branch("par_y", &parton_y);
    trackTree->Branch("par_z", &parton_z);
    trackTree->Branch("par_t", &parton_t);
    trackTree->Branch("par_color1", &parton_color1);
    trackTree->Branch("par_color2", &parton_color2);

    // After ZPC branches
    trackTree->Branch("par_pdgid_after_zpc", &parton_pid_after_zpc);
    trackTree->Branch("par_px_after_zpc", &parton_px_after_zpc);
    trackTree->Branch("par_py_after_zpc", &parton_py_after_zpc);
    trackTree->Branch("par_pz_after_zpc", &parton_pz_after_zpc);
    trackTree->Branch("par_e_after_zpc", &parton_e_after_zpc);
    trackTree->Branch("par_x_after_zpc", &parton_x_after_zpc);
    trackTree->Branch("par_y_after_zpc", &parton_y_after_zpc);
    trackTree->Branch("par_z_after_zpc", &parton_z_after_zpc);
    trackTree->Branch("par_t_after_zpc", &parton_t_after_zpc);
    trackTree->Branch("par_color1_after_zpc", &parton_color1_after_zpc);
    trackTree->Branch("par_color2_after_zpc", &parton_color2_after_zpc);

    trackTree->Branch("px", &genpx);
    trackTree->Branch("py", &genpy);
    trackTree->Branch("pz", &genpz);
    trackTree->Branch("m", &genm);
    trackTree->Branch("pid", &genpid);
    trackTree->Branch("chg", &genchg);

    trackTree->Branch("genJetEta", &genJetEta);
    trackTree->Branch("genJetPt", &genJetPt);
    trackTree->Branch("genJetPhi", &genJetPhi);
    trackTree->Branch("genJetChargedMultiplicity", &genJetChargedMultiplicity);
    trackTree->Branch("Zgs", &Zgs);
    trackTree->Branch("Rgs", &Rgs);
    trackTree->Branch("ZgTgBs", &ZgTgBs);
    trackTree->Branch("SDJetMass", &SDJetMass);
    trackTree->Branch("genDau_chg", &gendau_chg);
    trackTree->Branch("genDau_pid", &gendau_pid);
    trackTree->Branch("genDau_pt", &gendau_pt);
    trackTree->Branch("genDau_eta", &gendau_eta);
    trackTree->Branch("genDau_phi", &gendau_phi);

    int njetevent_count = 0;

    //*******************************START EVENT LOOP****************************************
    for (int iev = 0; iev < Nevent; iev++)
    {
	// Clear before ZPC vectors
	parton_pid.clear();
	parton_px.clear();
	parton_py.clear();
	parton_pz.clear();
	parton_e.clear();
	parton_x.clear();
	parton_y.clear();
	parton_z.clear();
	parton_t.clear();
	parton_color1.clear();
	parton_color2.clear();

	// Clear after ZPC vectors
	parton_pid_after_zpc.clear();
	parton_px_after_zpc.clear();
	parton_py_after_zpc.clear();
	parton_pz_after_zpc.clear();
	parton_e_after_zpc.clear();
	parton_x_after_zpc.clear();
	parton_y_after_zpc.clear();
	parton_z_after_zpc.clear();
	parton_t_after_zpc.clear();
	parton_color1_after_zpc.clear();
	parton_color2_after_zpc.clear();

	genpx.clear();
	genpy.clear();
	genpz.clear();
	genm.clear();
	genpid.clear();
	genchg.clear();

	genJetPt.clear();
	genJetEta.clear();
	genJetPhi.clear();
	genJetChargedMultiplicity.clear();
	Zgs.clear();
	Rgs.clear();
	ZgTgBs.clear();
	SDJetMass.clear();
	gendau_chg.clear();
	gendau_pid.clear();
	gendau_pt.clear();
	gendau_eta.clear();
	gendau_phi.clear();

	// PARTON stuff

	int numPartons;
	if (inputFile_p.eof())
	{
		cout << "end the file" << endl;
		break;
	}
	while (getline(inputFile_p, line2))
	{
		if (line2.empty() || line2[0] == '#') continue;
		break;
	}
	istringstream iss(line2);
	iss >> numPartons;

	if (inputFile_h.eof())
	{
		cout << "end the hadron file" << endl;
		break;
	}
	int idx, nHadrons, z3, z4;
	while (getline(inputFile_h, lineh))
	{
		istringstream issh(lineh);
		issh >> idx >> nHadrons >> z3 >> z4;
		if (nHadrons > 0) break;

		// Skip 0-hadron events
		for (int i = 0; i < numPartons; ++i)
			inputFile_p >> par_pdgid >> par_px >> par_py >> par_pz >> par_e >> par_x >> par_y >> par_z >> par_t >> mid1 >> mid2;
		
		// Skip ZPC data for this event too
		int skip_zpc_event, skip_zpc_dummy, skip_zpc_npartons;
		float skip_zpc_dummy_f;
		inputFile_zpc >> skip_zpc_event >> skip_zpc_dummy >> skip_zpc_npartons >> skip_zpc_dummy_f >> skip_zpc_dummy >> skip_zpc_dummy >> skip_zpc_dummy >> skip_zpc_dummy;
		for (int i = 0; i < skip_zpc_npartons; ++i) {
			int skip_pid, skip_c1, skip_c2;
			float skip_px, skip_py, skip_pz, skip_mass, skip_x, skip_y, skip_z, skip_t;
			inputFile_zpc >> skip_pid >> skip_px >> skip_py >> skip_pz >> skip_mass >> skip_x >> skip_y >> skip_z >> skip_t >> skip_c1 >> skip_c2;
		}
		while (getline(inputFile_p, line2))
		{
			if (line2.empty() || line2[0] == '#') continue;
			break;
		}
		istringstream iss(line2);
		iss >> numPartons;

		if (inputFile_p.eof() || inputFile_h.eof()) 
            	{
                	cout << "Skip until EOF" << endl;
                	break;
            	}
	}

	for (int i = 0; i < numPartons; ++i)
	{
		inputFile_p >> par_pdgid >> par_px >> par_py >> par_pz >> par_e >> par_x >> par_y >> par_z >> par_t >> mid1 >> mid2;

		parton_pid.push_back(par_pdgid);
		parton_px.push_back(par_px);
		parton_py.push_back(par_py);
		parton_pz.push_back(par_pz);
		parton_e.push_back(par_e);
		parton_x.push_back(par_x);
		parton_y.push_back(par_y);
		parton_z.push_back(par_z);
		parton_t.push_back(par_t);
		parton_color1.push_back((int)mid1);
		parton_color2.push_back((int)mid2);
	}

	// Read ZPC.dat (partons after rescattering) for this event
	if (inputFile_zpc.eof()) {
		cout << "End of ZPC file" << endl;
		break;
	}

	// Read ZPC event header
	int zpc_event, zpc_dummy, zpc_npartons;
	float zpc_dummy_f;
	inputFile_zpc >> zpc_event >> zpc_dummy >> zpc_npartons >> zpc_dummy_f >> zpc_dummy >> zpc_dummy >> zpc_dummy >> zpc_dummy;

	// Create temporary storage for ZPC partons
	vector<int> zpc_pid;
	vector<float> zpc_px, zpc_py, zpc_pz, zpc_mass, zpc_x, zpc_y, zpc_z, zpc_t;
	vector<int> zpc_color1, zpc_color2;

	// Read all ZPC partons for this event
	for (int j = 0; j < zpc_npartons; ++j) {
		int pid, c1, c2;
		float px, py, pz, mass, x, y, z, t;
		
		if (inputFile_zpc >> pid >> px >> py >> pz >> mass >> x >> y >> z >> t >> c1 >> c2) {
			zpc_pid.push_back(pid);
			zpc_px.push_back(px);
			zpc_py.push_back(py);
			zpc_pz.push_back(pz);
			zpc_mass.push_back(mass);
			zpc_x.push_back(x);
			zpc_y.push_back(y);
			zpc_z.push_back(z);
			zpc_t.push_back(t);
			zpc_color1.push_back(c1);
			zpc_color2.push_back(c2);
		}
	}

	// Match partons by color indices and store in after_zpc vectors
	for (size_t i = 0; i < parton_color1.size(); ++i) {
		bool found = false;
		for (size_t j = 0; j < zpc_color1.size(); ++j) {
			if (parton_color1[i] == zpc_color1[j] && parton_color2[i] == zpc_color2[j]) {
				parton_pid_after_zpc.push_back(zpc_pid[j]);
				parton_px_after_zpc.push_back(zpc_px[j]);
				parton_py_after_zpc.push_back(zpc_py[j]);
				parton_pz_after_zpc.push_back(zpc_pz[j]);
				// Convert mass to energy: E = sqrt(p^2 + m^2)
				float p2 = zpc_px[j]*zpc_px[j] + zpc_py[j]*zpc_py[j] + zpc_pz[j]*zpc_pz[j];
				parton_e_after_zpc.push_back(sqrt(p2 + zpc_mass[j]*zpc_mass[j]));
				parton_x_after_zpc.push_back(zpc_x[j]);
				parton_y_after_zpc.push_back(zpc_y[j]);
				parton_z_after_zpc.push_back(zpc_z[j]);
				parton_t_after_zpc.push_back(zpc_t[j]);
				parton_color1_after_zpc.push_back(zpc_color1[j]);
				parton_color2_after_zpc.push_back(zpc_color2[j]);
				found = true;
				break;
			}
		}
		if (!found) {
			// If no match found, fill with dummy values
			parton_pid_after_zpc.push_back(-999);
			parton_px_after_zpc.push_back(-999);
			parton_py_after_zpc.push_back(-999);
			parton_pz_after_zpc.push_back(-999);
			parton_e_after_zpc.push_back(-999);
			parton_x_after_zpc.push_back(-999);
			parton_y_after_zpc.push_back(-999);
			parton_z_after_zpc.push_back(-999);
			parton_t_after_zpc.push_back(-999);
			parton_color1_after_zpc.push_back(-999);
			parton_color2_after_zpc.push_back(-999);
			cout << "Warning: No ZPC match found for parton with colors " << parton_color1[i] << ", " << parton_color2[i] << endl;
		}
	}

	// PARTICLE stuff

	// test infile status
	if (feof(infile))
	{
		event_loop_flag = 0;
		cout << " End the event loop ~~~ " << endl;
		break;
	}

	fscanf(infile, "%s %d\n", stemp1, &total_number_of_particles);
	cout << "nHadrons: " << nHadrons << "\ttotal_number_of_particles: " << total_number_of_particles << endl;
	input_particles.clear();
	//******************START daughter particles LOOP********************************
	for (auto i = 0; i < total_number_of_particles; i++)
	{
		if (feof(infile))
		{
			event_loop_flag = 0;
			cout << " End the event loop, and drop last event ~~~ " << endl;
			break;
		}
		fscanf(infile, "%d %lf %lf %lf %lf %lf\n", &pid, &mass,
		       &energy, &px, &py, &pz);
		if (isnan(energy) || isnan(px) || isnan(py) || isnan(pz))
			continue;
		fastjet::PseudoJet particle = PseudoJet(px, py, pz, energy);
		particle.set_user_index(pid);
		input_particles.push_back(particle);

		genpx.push_back(px);
		genpy.push_back(py);
		genpz.push_back(pz);
		genm.push_back(mass);
		genpid.push_back(pid);
		genchg.push_back(particleData.charge(pid));
	} //**************************END daughter partcicles LOOP**********************************

	if (event_loop_flag == 0)
	{
		cout << " End the event loop and drop last event ~~~ " << endl;
		break;
	}

	count_event_number++;

	// Then do the jet finding
	// fastjet::Selector particle_selector = fastjet::SelectorAbsEtaMax(absetamax) && fastjet::SelectorPtMin( particle_ptmin );
	fastjet::JetDefinition jet_def(fastjet::antikt_algorithm, R_jet);
	// select jet
	// fastjet::Selector jet_selector = fastjet::SelectorAbsEtaMax( jet_absetamax ) && fastjet::SelectorPtMin( jet_ptmin );
	// input_particles = particle_selector(input_particles);
	fastjet::ClusterSequence clust_seq(input_particles, jet_def);
	// get the resulting jets ordered in pt
	vector<fastjet::PseudoJet> inclusive_jets = sorted_by_pt(clust_seq.inclusive_jets());

	// Select the jet pT and output the selected events, rotate the jet at pz direction
	//*************************************START JET LOOP*****************************************
	for (unsigned int i = 0; i < inclusive_jets.size(); i++)
	{
		if (inclusive_jets[i].pt() < jet_ptmin)
			continue;
		std::vector<float> tmp_pt;
		std::vector<float> tmp_eta;
		std::vector<float> tmp_phi;
		std::vector<int> tmp_chg;
		std::vector<int> tmp_pid;
		vector<PseudoJet> constituents = inclusive_jets[i].constituents();
		int chMult = 0;
		//***********************START constituents LOOP*********************************
		for (unsigned j = 0; j < constituents.size(); j++)
		{
			if (particleData.charge(constituents[j].user_index()))
			{
				chMult++;
			}
			tmp_pt.push_back(constituents[j].pt());
			tmp_eta.push_back(constituents[j].eta());
			tmp_phi.push_back(constituents[j].phi());
			tmp_chg.push_back(particleData.charge(constituents[j].user_index()));
			tmp_pid.push_back(constituents[j].user_index());
		}
		//***********************END constituents LOOP*********************************

		genJetPt.push_back(inclusive_jets[i].pt());
		genJetEta.push_back(inclusive_jets[i].eta());
		genJetPhi.push_back(inclusive_jets[i].phi());
		genJetChargedMultiplicity.push_back(chMult);
		gendau_pt.push_back(tmp_pt);
		gendau_eta.push_back(tmp_eta);
		gendau_phi.push_back(tmp_phi);
		gendau_chg.push_back(tmp_chg);
		gendau_pid.push_back(tmp_pid);

		// SoftDrop
		fastjet::PseudoJet sd_jet = softdrop(inclusive_jets[i]);
		if (!sd_jet.has_structure_of<fastjet::contrib::SoftDrop>()) 
		{
			Zgs.push_back(-2);
			Rgs.push_back(-2);
			ZgTgBs.push_back(-2);
                        SDJetMass.push_back(-2);
                        continue;
		}

		fastjet::PseudoJet parent1;
		fastjet::PseudoJet parent2;
		if (!sd_jet.has_parents(parent1,parent2))
		{
			Zgs.push_back(-1);
			Rgs.push_back(-1);
			ZgTgBs.push_back(-1);
			SDJetMass.push_back(-1);
			continue;
		}

		Zgs.push_back(sd_jet.structure_of<fastjet::contrib::SoftDrop>().symmetry());
		Rgs.push_back(sd_jet.structure_of<fastjet::contrib::SoftDrop>().delta_R());
		ZgTgBs.push_back(Zgs[i] * Rgs[i] / R_jet);
		SDJetMass.push_back(sd_jet.m());

	} //************************************END JET LOOP******************************************
	trackTree->Fill();
    }//****************************************END EVENT LOOP***************************************

	fclose(infile);
	inputFile_p.close();
	inputFile_zpc.close();
    //TFile * fout = TFile::Open( Form("/eos/cms/store/group/phys_heavyions/huangxi/PC/pp_parton_cascade_%d.root",jobnumber) ,"recreate");
    TFile * fout = TFile::Open( Form("/eos/cms/store/group/phys_heavyions/xiaoyul/wenbin/sample/pp_parton_cascade_%d.root",jobnumber) ,"recreate");
	trackTree->Write();
    fout->Close();
    return 0;
}

