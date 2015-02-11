SELECT process.daterun,processtype.displayname, instrument.name, process_udf_view."udfvalue" RunID, researcher.initials, substr(artifact_udf_view."udfname",1, instr(artifact_udf_view."udfname",'R',-1 )-1 ) Runfield, sum(to_number(artifact_udf_view."udfvalue" ))/2 uvalue 
FROM claritylims.process, claritylims.process_udf_view, claritylims.processtype, claritylims.processiotracker , claritylims.artifact_udf_view, claritylims.researcher, claritylims.instrument, claritylims.installation 
WHERE process.typeid = processtype.typeid
AND process.installationid = installation.id
AND installation.instrumentid = instrument.instrumentid 
AND process.processid = processiotracker.processid 
AND process.processid = process_udf_view.processid
AND process_udf_view."udfname" ='Run ID'
AND  processiotracker.inputartifactid = artifactid
AND process.ownerid = researcher.researcherid
AND DISPLAYNAME = 'MiSeq Run (MiSeq) 4.0 v1.0.0' 
and artifact_udf_view."udfname" in ('Cluster Density (K/mm^2) R1','Cluster Density (K/mm^2) R2','% Aligned R1','% Aligned R2','% Error Rate R1','% Error Rate R2', '% Bases >=Q30 R1', '% Bases >=Q30 R2', '%PF R1', '%PF R2')
group by process.daterun, processtype.displayname, instrument.name, process_udf_view."udfvalue", researcher.initials, substr(artifact_udf_view."udfname",1, instr(artifact_udf_view."udfname",'R',-1 )-1 ) 
ORDER BY process.daterun DESC, process_udf_view."udfvalue";
