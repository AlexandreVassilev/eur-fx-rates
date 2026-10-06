// Runs tests/page_tests.js in Apple's JavaScript engine (the one inside Safari).
// Called by tests/test_page.py:
//   osascript -l JavaScript tests/page_tests_mac.js <project folder> <start_end> <start_end> ...
// Prints the results as JSON.

ObjC.import("Foundation");

function read(path) {
  return $.NSString.stringWithContentsOfFileEncodingError(path, $.NSUTF8StringEncoding, null).js;
}

function run(argv) {
  const project = argv[0];
  const FX = eval(read(`${project}/app.js`) + "\n;FX");
  const runPageTests = eval(read(`${project}/tests/page_tests.js`) + "\n;runPageTests");
  const settings = JSON.parse(read(`${project}/settings.json`));
  const ranges = argv.slice(1).map(range => range.split("_"));
  return JSON.stringify(runPageTests(FX, read(`${project}/data/export_all.csv`), settings.csv_delimiter, ranges));
}
