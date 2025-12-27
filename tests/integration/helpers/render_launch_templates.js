// Helper script to synthesize Pulumi resources with mocks and emit LaunchTemplate details as JSON.
// This allows integration tests to validate preview/up expectations without AWS credentials.

const path = require("path");
const Module = require("module");

// Ensure pulumi dependencies are resolved from the project package tree.
const agentNodeModules = path.resolve(__dirname, "..", "..", "..", "pulumi", "jenkins-agent", "node_modules");
if (!Module.globalPaths.includes(agentNodeModules)) {
  Module.globalPaths.push(agentNodeModules);
}
process.env.NODE_PATH = [agentNodeModules, process.env.NODE_PATH || ""].filter(Boolean).join(path.delimiter);
Module._initPaths();

// Silence noisy program-level console output to keep stdout JSON-only.
const originalConsoleLog = console.log;
console.log = process.env.PULUMI_MOCK_DEBUG ? originalConsoleLog : () => {};

const runtime = require("@pulumi/pulumi/runtime");

const DEFAULT_STACK = "test";
const capturedLaunchTemplates = [];
let stackOutputs = {};
let resourceCount = 0;
let programExports = [];

const ssmValueBySuffix = {
  "config/project-name": "jenkins-infra",
  "config/agent-max-capacity": "4",
  "config/agent-min-capacity": "1",
  "config/agent-spot-price": "0.010",
  "config/agent-instance-type": "t3.micro",
  "config/agent-spot-price-medium": "0.020",
  "config/agent-spot-price-small": "0.015",
  "config/agent-spot-price-micro": "0.010",
  "config/agent-medium-min-capacity": "1",
  "config/agent-medium-max-capacity": "2",
  "config/agent-small-min-capacity": "1",
  "config/agent-small-max-capacity": "2",
  "config/agent-micro-min-capacity": "1",
  "config/agent-micro-max-capacity": "2",
  "network/vpc-id": "vpc-123456",
  "network/private-subnet-a-id": "subnet-a",
  "network/private-subnet-b-id": "subnet-b",
  "security/jenkins-agent-sg-id": "sg-jenkins-agent",
  "agent-ami/custom-ami-x86": "ami-placeholder-x86",
  "agent-ami/custom-ami-arm": "ami-placeholder-arm",
};

const mockIdFor = (name) => `${name}-id`;

runtime.setMocks(
  {
    newResource: function (args) {
      if (process.env.PULUMI_MOCK_DEBUG) {
        console.error("newResource", args.type, args.name);
      }
      resourceCount += 1;
      if (args.type === "aws:ec2/launchTemplate:LaunchTemplate") {
        capturedLaunchTemplates.push({
          urn: args.urn,
          name: args.name,
          state: { ...args.inputs },
        });
      }
      if (args.type === "pulumi:pulumi:Stack") {
        stackOutputs = args.inputs?.outputs || {};
      }
      // Preserve inputs as state so listResourceOutputs reflects requested values.
      return {
        id: mockIdFor(args.name),
        state: {
          ...args.inputs,
          arn: args.inputs.arn || `${args.name}-arn`,
        },
      };
    },
    call: function (args) {
      const callArgs = args?.args || args?.inputs || {};
      if (process.env.PULUMI_MOCK_DEBUG) {
        console.error("call", args.token, callArgs);
      }
      if (args.token === "aws:ssm/getParameter:getParameter") {
        const name = callArgs.name || "";
        const suffix = name.split("/").slice(-2).join("/");
        const value = ssmValueBySuffix[suffix] || "mock-value";
        return { value };
      }

      if (args.token === "aws:ec2/getAmi:getAmi") {
        return {
          id: "ami-1234567890",
          name: "mock-ami",
        };
      }

      if (args.token === "aws:ec2/getSubnet:getSubnet") {
        const id = callArgs.id || mockIdFor("subnet");
        const zone = id.endsWith("b") ? "us-test-1b" : "us-test-1a";
        return {
          id,
          availabilityZone: zone,
        };
      }

      return {
        id: mockIdFor(args.token.replace(/[:/]/g, "-")),
        ...callArgs,
      };
    },
},
  "jenkins-agent",
  DEFAULT_STACK,
  true
);

async function main() {
  // Import compiled Pulumi program after mocks are installed.
  const compiledIndexPath = path.resolve(
    __dirname,
    "..",
    "..",
    "..",
    "pulumi",
    "jenkins-agent",
    "bin",
    "index.js"
  );
  try {
    await runtime.runInPulumiStack(async () => {
      const program = await import(compiledIndexPath);
      programExports = Object.keys(program || {}).filter(
        (key) => key !== "default" && key !== "__esModule"
      );
    });
  } catch (error) {
    console.error("Pulumi synthesis failed", error);
    throw error;
  }

  // Allow any deferred mock registrations to flush.
  for (let i = 0; i < 5 && resourceCount <= 1; i += 1) {
    await new Promise((resolve) => setTimeout(resolve, 10));
  }

  const summary = {
    launchTemplates: capturedLaunchTemplates.map((res) => ({
      urn: res.urn,
      name: res.name,
      namePrefix: res.state.namePrefix,
      creditSpecification: res.state.creditSpecification || {},
      metadataOptions: res.state.metadataOptions || {},
      networkInterfaces: res.state.networkInterfaces || [],
      blockDeviceMappings: res.state.blockDeviceMappings || [],
      tagSpecifications: res.state.tagSpecifications || [],
      userData: res.state.userData,
    })),
    exports: programExports,
    resourceCount,
  };

  process.stdout.write(JSON.stringify(summary, null, 2));
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
