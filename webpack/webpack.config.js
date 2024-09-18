const product = "bes.lims"
const src_path = "../src/bes/lims/browser/static"

const path = require("path");
const webpack = require("webpack");
const childProcess = require("child_process");

const CssMinimizerPlugin = require("css-minimizer-webpack-plugin");
const HtmlWebpackPlugin = require("html-webpack-plugin");
const MiniCssExtractPlugin = require("mini-css-extract-plugin");
const TerserPlugin = require('terser-webpack-plugin');
const { CleanWebpackPlugin } = require("clean-webpack-plugin");

const staticPath = path.resolve(__dirname, src_path);

const devMode = process.env.mode == "development";
const prodMode = process.env.mode == "production";
const mode = process.env.mode;
console.log(`RUNNING WEBPACK IN '${mode}' MODE`);


module.exports = {
  context: path.resolve(__dirname, "app"),
  // https://webpack.js.org/configuration/mode/#usage
  mode: mode,
  entry: {
    [product]: [
      `./${product}.coffee`,
      `./scss/${product}.scss`
    ],
  },
  output: {
    filename: devMode ? "[name].js" : "[name].[chunkhash].js",
    path: path.resolve(staticPath, "bundles"),
    publicPath: `++plone++${product}.static/bundles`
  },
  module: {
    rules: [
      {
        // Coffee
        test: /\.(coffee)$/,
        exclude: [/node_modules/],
        use: ["babel-loader", "coffee-loader"]
      }, {
        // JS
        test: /\.(js|jsx)$/,
        exclude: [/node_modules/],
        use: ["babel-loader"]
      }, {
        // SCSS
        test: /\.s[ac]ss$/i,
        use: [MiniCssExtractPlugin.loader, "css-loader", "sass-loader"]
      }
    ]
  },
  optimization: {
    minimize: prodMode,
    minimizer: [
      // https://v4.webpack.js.org/plugins/terser-webpack-plugin/
      new TerserPlugin({
        exclude: /\/modules/,
        terserOptions: {
          // https://github.com/webpack-contrib/terser-webpack-plugin#terseroptions
          sourceMap: false, // Must be set to true if using source-maps in production
          format: {
            comments: false
          },
          compress: {
            drop_console: true,
            passes: 2,
          },
        }
      }),
      // https://webpack.js.org/plugins/css-minimizer-webpack-plugin/
      new CssMinimizerPlugin({
        exclude: /\/modules/,
        minimizerOptions: {
          preset: [
            "default",
            {
              discardComments: { removeAll: true },
            },
          ],
        },
      }),
    ],
  },
  plugins: [
    // https://webpack.js.org/plugins/mini-css-extract-plugin/
    new MiniCssExtractPlugin({
      filename: devMode ? "[name].css" : "[name].[chunkhash].css",
    }),
    // https://github.com/johnagan/clean-webpack-plugin
    new CleanWebpackPlugin({
      verbose: false,
      // Workaround in `watch` mode when trying to remove the `resources.pt` in the parent folder:
      // Error: clean-webpack-plugin: Cannot delete files/folders outside the current working directory.
      cleanAfterEveryBuildPatterns: ["!../*"],
    }),
    // https://webpack.js.org/plugins/html-webpack-plugin/
    new HtmlWebpackPlugin({
      inject: false,
      filename:  path.resolve(staticPath, "resources.pt"),
      template: "resources.pt",
    }),
    // https://webpack.js.org/plugins/provide-plugin/
    new webpack.ProvidePlugin({
      $: "jquery",
      jQuery: "jquery",
    }),
  ],
  externals: {
    // https://webpack.js.org/configuration/externals
    $: "jQuery",
    jquery: "jQuery"
  }
};
