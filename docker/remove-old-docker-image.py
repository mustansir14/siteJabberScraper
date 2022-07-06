import sys, subprocess, json

imageNameWithVersion = sys.argv[1] if len( sys.argv ) > 1 else "";
if not imageNameWithVersion:
    print("Error: no container id")
    sys.exit
    
class Docker:
    
    class Image:
        
        def rm( self, imageID ):
            subprocess.run( [ "docker", "image", "rm", imageID ] )
    
    class Container:
        
        def execCmd(self, cmd):
            result = subprocess.run( cmd , stdout=subprocess.PIPE)
            
            out = []
            for line in result.stdout.decode('utf8').splitlines(True):
                out.append( json.loads( line ) )
                
            return out
        
        def all(self):
            cmd = [ 'docker', 'container', 'ls', '-a', '--format', '{{json . }}']
            return self.execCmd( cmd )
            
        def stop( self, containerID ):
            subprocess.run( [ "docker", "container", "stop", containerID ] )
            
        def rm( self, containerID ):
            subprocess.run( [ "docker", "container", "rm", containerID ] )
    
    @staticmethod
    def container():
        return Docker.Container()
        
    @staticmethod
    def image():
        return Docker.Image()
    
containers = Docker.container().all();
for container in containers:
    if container["Image"] == imageNameWithVersion:
        print("Stop image:",container['Image'],"...")
        Docker.container().stop( container["ID"] )
        
        print("Remove image:",container['Image'],"...")
        Docker.container().rm( container["ID"] )

print("Remove container '" + imageNameWithVersion + "'...");
Docker.image().rm( imageNameWithVersion );

    
   