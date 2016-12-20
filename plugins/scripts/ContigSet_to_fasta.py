#!/usr/bin/env python

# standard library imports
import os
import sys
import argparse
import logging
import string

# 3rd party imports
# None

# KBase imports
import biokbase.RNASeq.script_util as script_utils 
import biokbase.workspace.client  


# conversion method that can be called if this module is imported
# Note the logger has different levels it could be run.  See: https://docs.python.org/2/library/logging.html#logging-levels
# The default level is set to INFO which includes everything except DEBUG
def transform(workspace_service_url=None, shock_service_url=None, handle_service_url=None, 
              workspace_name=None,token=None,object_name=None, object_id=None, 
              object_version_number=None, object_reference=None,working_directory=None, output_file_name=None, 
              level=logging.INFO, logger=None):  
    """
    Converts KBaseAssembly.SingleEndLibrary to a Fasta file of assembledDNA.
    
    Args:
        workspace_service_url:  A url for the KBase Workspace service 
        shock_service_url: A url for the KBase SHOCK service.
        handle_service_url: A url for the KBase Handle Service.
        workspace_name: Name of the workspace
        object_name: Name of the object in the workspace 
        object_id: Id of the object in the workspace, mutually exclusive to object_name
        object_version_number: Version number of workspace object (ContigSet), defaults to most recent version
	object_reference: Object reference to the Workspace object
        working_directory: The working directory where the output file should be stored.
        output_file_name: The desired file name of the result file.
        level: Logging level, defaults to logging.INFO.
    
    Returns:
        A FASTA file containing assembled sequences from a KBase ContigSet object.
    
    Authors:
        Jason Baumohl, Matt Henderson
    
    """ 

    def insert_newlines(s, every):
        lines = []
        for i in xrange(0, len(s), every):
            lines.append(s[i:i+every])
        return "\n".join(lines)+"\n"


    if logger is None:
        logger = script_utils.stderrlogger(__file__)
    
    logger.info("Starting conversion of KBaseGenomes.ContigSet to FASTA.DNA.Assembly")

    #token = os.environ.get("KB_AUTH_TOKEN")

    if not os.path.isdir(args.working_directory): 
        raise Exception("The working directory does not exist {0} does not exist".format(working_directory)) 

    logger.info("Grabbing Data.")
 
    try:
        ws_client = biokbase.workspace.client.Workspace(workspace_service_url,token=token) 
        if object_version_number and object_name:
            #print "111-----------" + object_name + ":" + workspace_name
            contig_set = ws_client.get_objects([{"workspace":workspace_name,"name":object_name, "ver":object_version_number}])[0] 
        elif object_name:
            #print "222-----------" + object_name + ":" + workspace_name
            contig_set = ws_client.get_objects([{"workspace":workspace_name,"name":object_name}])[0]
            #print "222-----------"
        elif object_version_number and object_id:
            #print "333-----------" + object_id + ":" + workspace_name
            contig_set = ws_client.get_objects([{"workspace":workspace_name,"objid":object_id, "ver":object_version_number}])[0]
        elif object_reference:
	    contig_set = ws_client.get_objects([{'ref' : object_reference}])[0]
	else:
            #print "444-----------" + object_name + ":" + workspace_name
            contig_set = ws_client.get_objects([{"workspace":workspace_name,"objid":object_id}])[0] 
    except Exception, e: 
        logger.exception("Unable to retrieve workspace object from {0}:{1}.".format(workspace_service_url,workspace_name))
        logger.exception(e)
        raise 

    shock_id = None 
    if "fasta_ref" in contig_set["data"]: 
        shock_id = contig_set["data"]["fasta_ref"] 
        logger.info("Retrieving data from Shock.")
        script_utils.download_file_from_shock(logger = logger, 
                                              shock_service_url = shock_service_url, 
                                              shock_id = shock_id, 
                                              directory = working_directory, 
                                              token = token)
    else: 
        ws_object_name = contig_set["info"][1]
        logger.info("getting info {0}".format(ws_object_name))
        valid_chars = "-_.(){0}{1}".format(string.ascii_letters, string.digits)
        temp_file_name = ""
        filename_chars = list()
        
        for character in ws_object_name:
            if character in valid_chars:
                filename_chars.append(character)
            else:
                filename_chars.append("_")
        
        if len(filename_chars) == 0:
            temp_file_name = "ContigSetFile"
        else:
            temp_file_name = "".join(filename_chars)

        logger.warning("This ContigSet does not have a fasta_ref to shock.  The fasta file will be attempted to be built from contig sequences in the object.")
        
        output_file = os.path.join(working_directory,temp_file_name)
        if not contig_set["data"]["contigs"]:
            #The contig list is empty
            raise Exception("This ContigSet does not have a fasta_ref to shock and does not have any contigs. Likely due to the ContigSet being too large.")

        with open(output_file, "w") as outFile:
            for contig in contig_set["data"]["contigs"]:
                outFile.write(">{}\n".format(contig["id"]))
            
                #write 80 nucleotides per line
                if contig["sequence"] != "":
                    outFile.write(insert_newlines(contig["sequence"],80))
                else:
                    outFile.close()    
                    raise IOError("This ContigSet does not have a fasta_ref to shock or sequences in the contigs. A fasta file can not be created.  Likely dueto the ContigSet being too large.")
    
    if output_file_name is not None and len(output_file_name) > 0:
        name = os.listdir(working_directory)[0]
        os.rename(os.path.join(working_directory, name), os.path.join(working_directory, output_file_name))

    logger.info("Conversion completed.")


# called only if script is run from command line
if __name__ == "__main__":
    #script_details = script_utils.parse_docs(transform.__doc__)

    parser = argparse.ArgumentParser(prog=__file__, 
                                     description="Dowload script for ContigSet Object",
                                     epilog="Jason , Matt Henderson")
    
    # The following 8 arguments should be fairly standard to all uploaders
    parser.add_argument("--workspace_service_url", 
                        help="workspace_service_url", 
                        action="store", 
                        type=str, 
                        nargs="?", 
                        required=True)
    parser.add_argument("--workspace_name", 
                        help="workspace_name", 
                        action="store", 
                        type=str, 
                        nargs="?", 
                        required=True)
    parser.add_argument("--working_directory", 
                        help="working_directory", 
                        action="store", 
                        type=str, 
                        nargs="?", 
                        required=True)	

    parser.add_argument("--token",
                        help="Auth Token",
                        action="store",
                        type=str,
                        nargs="?",
                        required=False)

    parser.add_argument("--output_file_name", 
                        help="output_file_name", 
                        action="store", 
                        type=str, 
                        nargs="?", 
                        required=False)
    parser.add_argument("--object_version_number", 
                        help="object_version_number", 
                        action="store", 
                        type=int, 
                        nargs="?", 
                        required=False)

    object_info = parser.add_mutually_exclusive_group(required=True)
    object_info.add_argument("--object_name", 
                             help="object_name", 
                             action="store", 
                             type=str, 
                             nargs="?") 
    object_info.add_argument("--object_id", 
                             help="object_id", 
                             action="store", 
                             type=int, 
                             nargs="?")
    object_info.add_argument("--object_reference",
                             help="object_reference",
                             action="store",
                             type=str,
                             nargs="?")

    data_services = parser.add_mutually_exclusive_group(required=True) 
    data_services.add_argument("--shock_service_url", 
                        help="shock_service_url", 
                        action="store", 
                        type=str, 
                        nargs="?") 
    data_services.add_argument("--handle_service_url", 
                        help="handle_service_url", 
                        action="store", 
                        type=str, 
                        nargs="?")

    args = parser.parse_args()

    logger = script_utils.stderrlogger(__file__)
    logger.info("Starting download of ContigSet => FASTA")
    try:
        transform(workspace_service_url = args.workspace_service_url, 
                  shock_service_url = args.shock_service_url, 
                  handle_service_url = args.handle_service_url, 
                  workspace_name = args.workspace_name,
		  token = args.token, 
                  object_name = args.object_name, 
                  object_id = args.object_id, 
                  object_version_number = args.object_version_number,
		  object_reference = args.object_reference, 
                  output_file_name = args.output_file_name,
                  working_directory = args.working_directory, 
                  logger = logger)
    except Exception, e:
        logger.exception(e)
        sys.exit(1)
    
    sys.exit(0)
