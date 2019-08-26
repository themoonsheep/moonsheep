module.exports = function(grunt) {

  //Config
  grunt.initConfig({
    pkg: grunt.file.readJSON('package.json'),

    uglify: {
      options: {
        banner: '/* <%= pkg.name %> <%= grunt.template.today("dd/mm/yyyy") %> */\n'
      },
      build: {
        src: 'src/js/moonsheep.js',
        dest: 'js/<%= pkg.name %>.min.js'
      }
    },
    less: {
      build: {
        options: {
          paths: ['src/less', 'src/less/parts', 'src/less/conf']
        },
        files: {
          'css/main.css': 'src/less/main.less'
        }
      }
    },
    copy: {
			build: {
				files: [
					{
						src: 'src/vendor/jquery/dist/jquery.min.js',
						dest: 'assets/vendor/jquery.min.js'
					},
          {
						src: 'src/vendor/normalize-css/normalize.css',
						dest: 'assets/vendor/normalize.css'
					},
          {
            expand: true,
            cwd: 'src/assets',
            src: '**',
            dest: 'assets/'
          }
        ]
      }
    },

    watch: {
      uglify: {
        files: 'src/js/moonsheep.js',
        tasks: 'uglify:build'
      },
      less: {
        files: ['src/less/*', 'src/less/conf/*', 'src/less/parts/*'],
        tasks: 'less:build'
      }
    }

  });

  grunt.loadNpmTasks('grunt-contrib-watch');
  grunt.loadNpmTasks('grunt-contrib-uglify');
  grunt.loadNpmTasks('grunt-contrib-less');
  grunt.loadNpmTasks('grunt-contrib-copy');

  grunt.registerTask('default', ['watch']);
  grunt.registerTask('build', [
    'copy:build',
    'less:build',
    'uglify:build'
  ]);

}
