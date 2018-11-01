#ifndef FEMODEL_H
#define FEMODEL_H

#include "Domain.h"
#include "Matrix.h"

#include "siteLayering.h"
#include "soillayer.h"
#include "outcropMotion.h"

#define MAX_FREQUENCY 50.0
#define NODES_PER_WAVELENGTH 10

class SiteResponseModel {

public:
	SiteResponseModel();
	SiteResponseModel(SiteLayering, OutcropMotion*, OutcropMotion*);
	~SiteResponseModel();

	int   runTestModel();
	int   runTotalStressModel();
	void  setOutputDir(std::string outDir) { theOutputDir = outDir; };

private:
	Domain *theDomain;
	SiteLayering    SRM_layering;
	OutcropMotion*  theMotionX;
	OutcropMotion*  theMotionZ;
	std::string     theOutputDir;
};


#endif