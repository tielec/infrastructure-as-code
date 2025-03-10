import jenkins.model.Jenkins

// Disable CLI over Remoting
Jenkins.instance.getDescriptor("jenkins.CLI").get().setEnabled(false)
Jenkins.instance.save()
