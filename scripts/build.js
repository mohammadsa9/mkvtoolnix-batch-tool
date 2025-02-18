const { spawnSync } = require('child_process');

const spawnOptions = { detached: false, shell: true, stdio: 'inherit' };

/**
 * @namespace Builder
 * @description - Builds React & Python builds of project so Electron can be used.
 */

class Builder {

  /**
   * @description - Creates React and Python production builds.
   * @memberof Builder
   */
  buildAll = () => {
    const { buildPython, buildReact } = this;

    buildPython();
    buildReact();
  }

  /**
   * @description - Creates production build of Python back end.
   * @memberof Builder
   */
  buildPython = () => {
    // eslint-disable-next-line no-console
    console.log('Creating Python distribution files...');

    const app = 'app.py';
    const icon = './public/favicon.ico';

    // PyInstaller default options
    const pyInstallerOptions = [
      '--noconfirm', // Don't confirm overwrite
      '--distpath=./resources', // Output path
      `--icon=${icon}`, // Icon to use for app
      '--collect-datas=langdetect' // modules
    ];

    // Options for app file with hidden console
    const productionOptions = [
      ...pyInstallerOptions,
      '--noconsole' // Hides console output
    ];

    // Options for app file with console shown
    const debugOptions = [
      ...pyInstallerOptions,
      '--name=app.debug' // Custom name for debug app
    ];

    // Create production and debug versions of app
    spawnSync('pyinstaller', [...productionOptions, app], spawnOptions);
    spawnSync('pyinstaller', [...debugOptions, app], spawnOptions);
  }

  /**
   * @description - Creates production build of React front end.
   * @memberof Builder
   */
  buildReact = () => {
    // eslint-disable-next-line no-console
    console.log('Creating React distribution files...');

    // Set the GENERATE_SOURCEMAP environment variable to false
    process.env.GENERATE_SOURCEMAP = 'false';

    spawnSync('react-scripts build', spawnOptions);
  }
}

module.exports.Builder = Builder;
