from resource_management import *
import os

def create_hdfs_dir(path, owner, perms):
  Execute("hadoop fs -mkdir -p %s" % (path), user='hdfs')
  Execute("hadoop fs -chown %s %s" % (owner, path), user='hdfs')
  Execute("hadoop fs -chmod %s %s" % (str(perms), path), user='hdfs')

def package(name):
  import params
  Execute("%s install -y %s" % (params.package_mgr, name), user='root')

def add_repo(source, dest):
  import params
  if not os.path.isfile(dest + params.repo_file):
    Execute("cp %s %s" % (source, dest))
    Execute(params.key_cmd)
    Execute(params.cache_cmd)

def cdap_config(name=None):
  import params
  print 'Setting up CDAP configuration for ' + name
  # We're only setup for *NIX, for now
  Directory(params.etc_prefix_dir,
            mode=0755
  )

  Directory(params.cdap_conf_dir,
            owner = params.cdap_user,
            group = params.user_group,
            recursive = True
  )

  XmlConfig('cdap-site.xml',
            conf_dir = params.cdap_conf_dir,
            configurations = params.config['configurations']['cdap-site'],
            owner = params.cdap_user,
            group = params.user_group
  )

  File(format("{params.cdap_conf_dir}/cdap-env.sh"),
       owner = params.cdap_user,
       content=InlineTemplate(params.cdap_env_sh_template)
  )

  if name == 'auth':
    dirname = 'security'
  elif name == 'router':
    dirname = 'gateway'
  else:
    dirname = name

  cleanup_opts(dirname)

  # Copy logback.xml and logback-container.xml
  for i in 'logback.xml', 'logback-container.xml':
    no_op_test = "ls %s/%s 2>/dev/null" % (params.cdap_conf_dir, i)
    Execute("cp -f /etc/cdap/conf.dist/%s %s" % (i, params.cdap_conf_dir), not_if=no_op_test)

  Execute("update-alternatives --install /etc/cdap/conf cdap-conf %s 50" % (params.cdap_conf_dir))

def has_hive():
  import params
  if len(params.hive_metastore_host) > 0:
    return true
  else:
    return false

def get_hdp_version():
  command = 'hadoop version'
  return_code, hdp_output = shell.call(command, timeout=20)

  if return_code != 0:
    raise Fail("Unable to determine the current hadoop version: %s" % (hdp_output))

  line = hdp_output.rstrip().split('\n')[0]
  arr = line.split('.')
  hdp_version = "%s.%s.%s.%s" % (arr[3], arr[4], arr[5], arr[6])
  match = re.match('[0-9]+.[0-9]+.[0-9]+.[0-9]+-[0-9]+', hdp_version)
  if match is None:
    raise Fail('Failed to get extracted version')
  return hdp_version

def get_hadoop_lib():
  v = get_hdp_version()
  arr = v.split('.')
  maj_min = float("%s.%s" % (arr[0], arr[1]))
  if maj_min >= 2.2:
    hadoop_lib = "/usr/hdp/%s/hadoop/lib" % (v)
  else:
    hadoop_lib = '/usr/lib/hadoop/lib'
  return hadoop_lib

def cleanup_opts(dirname):
  command = "sed -i 's/\"$OPTS\"/$OPTS/g' /opt/cdap/%s/bin/service" % (dirname)
  # We ignore errors here, in case we are called before package installation
  shell.call(command, timeout=20)