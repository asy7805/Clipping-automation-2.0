# Clipping Automation 2.0 Makefile

init-stream:
	python3 scripts/init_stream_dirs.py --channel $${CHANNEL} --ingest-type $${TYPE} --chunk-seconds $${CHUNK} --output-root $${OUTPUT_ROOT:-./streams}

# make init-stream CHANNEL=example_channel TYPE=vod CHUNK=60
# make init-stream CHANNEL=example_channel TYPE=vod CHUNK=60 OUTPUT_ROOT=/custom/path
