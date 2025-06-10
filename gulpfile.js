const browsersync = require("browser-sync").create();
const cached = require("gulp-cached");
const cssnano = require("gulp-cssnano");
const del = require("del");
const fileinclude = require("gulp-file-include");
const gulp = require("gulp");
const { dest } = require("gulp");
const gulpif = require("gulp-if");
const npmdist = require("gulp-npm-dist");
const replace = require("gulp-replace");
const uglify = require("gulp-uglify");
const useref = require("gulp-useref-plus");
const rename = require("gulp-rename");
const sass = require("gulp-sass")(require("sass"));
const autoprefixer = require("gulp-autoprefixer");
const sourcemaps = require("gulp-sourcemaps");
const cleanCSS = require("gulp-clean-css");
const rtlcss = require("gulp-rtlcss");
const newer = require("gulp-newer");

const app = "./metrica";

const paths = {
  base: {
    base: {
      dir: "./",
    },
    node: {
      dir: "./node_modules",
    },
    packageLock: {
      files: "./package-lock.json",
    },
  },
  dist: {
    libs: {
      dir: app + "/static/libs",
    },
    images: {
      dir: app + "/static/images",
    },
    fonts: {
      dir: app + "/static/fonts",
    },
    css: {
      dir: app + "/static/css",
    },
    js: {
      dir: app + "/static/js",
      files: app + "/static/js/pages",
    },
  },
  src: {
    css: {
      dir: app + "/static/source/css",
      files: app + "/static/source/css/**/*",
    },
    images: {
      dir: app + "/static/source/images",
      files: app + "/static/source/images/**/*",
    },
    fonts: {
      dir: app + "/static/source/fonts",
      files: app + "/static/source/fonts/**/*",
    },
    js: {
      dir: app + "/static/source/js",
      pages: app + "/static/source/js/pages",
      files: app + "/static/source/js/pages/*.js",
      main: app + "/static/source/js/*.js",
    },
    scss: {
      dir: app + "/static/source/scss",
      files: app + "/static/source/scss/**/*",
      icons: app + "/static/source/scss/icons.scss",
      main: app + "/static/source/scss/app*.scss",
      bootstrap: app + "/static/source/scss/bootstrap*.scss",
    },
  },
};

gulp.task("watch", function () {
  gulp.watch(paths.src.js.dir, gulp.series("js"));
  gulp.watch(paths.src.images.dir, gulp.series("images"));
  gulp.watch(paths.src.js.pages, gulp.series("jsPages"));
  gulp.watch(paths.src.scss.icons, gulp.series("icons"));
  gulp.watch(
    [
      paths.src.scss.bootstrap,
      "!" + paths.src.scss.main,
      "!" + paths.src.scss.icons,
    ],
    gulp.series("bootstrap")
  );
  gulp.watch(
    [
      paths.src.scss.files,
      "!" + paths.src.scss.bootstrap,
      "!" + paths.src.scss.icons,
    ],
    gulp.series("scss")
  );
});

gulp.task("js", function () {
  return gulp
    .src(paths.src.js.main)
    .pipe(uglify())
    .pipe(gulp.dest(paths.dist.js.dir));
});

gulp.task("jsPages", function () {
  return gulp
    .src(paths.src.js.files)
    .pipe(uglify())
    .pipe(gulp.dest(paths.dist.js.files));
});

//  Compile app scss
gulp.task("scss", function () {
  // generate ltr
  gulp
    .src([
      paths.src.scss.main,
      "!" + paths.src.scss.bootstrap,
      "!" + paths.src.scss.icons,
    ])
    .pipe(sourcemaps.init())
    .pipe(sass().on("error", sass.logError))
    .pipe(autoprefixer())
    .pipe(gulp.dest(paths.dist.css.dir))
    .pipe(cleanCSS())
    .pipe(
      rename({
        suffix: ".min",
      })
    )
    .pipe(sourcemaps.write("./"))
    .pipe(gulp.dest(paths.dist.css.dir));

  // generate rtl
  return gulp
    .src([
      paths.src.scss.main,
      "!" + paths.src.scss.bootstrap,
      "!" + paths.src.scss.icons,
    ])
    .pipe(sourcemaps.init())
    .pipe(sass().on("error", sass.logError))
    .pipe(autoprefixer())
    .pipe(rtlcss())
    .pipe(gulp.dest(paths.dist.css.dir))
    .pipe(cleanCSS())
    .pipe(
      rename({
        suffix: "-rtl.min",
      })
    )
    .pipe(sourcemaps.write("./"))
    .pipe(gulp.dest(paths.dist.css.dir));
});

//  Compile bootstrap scss
gulp.task("bootstrap", function () {
  // generate ltr
  gulp
    .src([
      paths.src.scss.bootstrap,
      "!" + paths.src.scss.main,
      "!" + paths.src.scss.icons,
    ])
    .pipe(sourcemaps.init())
    .pipe(sass().on("error", sass.logError))
    .pipe(autoprefixer())
    .pipe(gulp.dest(paths.dist.css.dir))
    .pipe(cleanCSS())
    .pipe(
      rename({
        suffix: ".min",
      })
    )
    .pipe(sourcemaps.write("./"))
    .pipe(gulp.dest(paths.dist.css.dir));

  // generate rtl
  return gulp
    .src([
      paths.src.scss.bootstrap,
      "!" + paths.src.scss.main,
      "!" + paths.src.scss.icons,
    ])
    .pipe(sourcemaps.init())
    .pipe(sass().on("error", sass.logError))
    .pipe(autoprefixer())
    .pipe(rtlcss())
    .pipe(gulp.dest(paths.dist.css.dir))
    .pipe(cleanCSS())
    .pipe(
      rename({
        suffix: "-rtl.min",
      })
    )
    .pipe(sourcemaps.write("./"))
    .pipe(gulp.dest(paths.dist.css.dir));
});

//  Compile Icons
gulp.task("icons", function () {
  return gulp
    .src(paths.src.scss.icons)
    .pipe(sourcemaps.init())
    .pipe(sass().on("error", sass.logError))
    .pipe(gulp.dest(paths.dist.css.dir))
    .pipe(cleanCSS())
    .pipe(
      rename({
        suffix: ".min",
      })
    )
    .pipe(sourcemaps.write("./"))
    .pipe(gulp.dest(paths.dist.css.dir));
});

gulp.task("images", function () {
  return gulp
    .src(paths.src.images.files)
    .pipe(newer(paths.dist.images.dir))
    .pipe(gulp.dest(paths.dist.images.dir));
});

gulp.task("fonts", function () {
  return gulp
    .src(paths.src.fonts.files)
    .pipe(newer(paths.dist.fonts.dir))
    .pipe(gulp.dest(paths.dist.fonts.dir));
});

gulp.task("copy:libs", function () {
  return gulp
    .src(npmdist(), { base: paths.base.node.dir })
    .pipe(
      rename(function (path) {
        path.dirname = path.dirname.replace(/\/dist/, "").replace(/\\dist/, "");
      })
    )
    .pipe(gulp.dest(paths.dist.libs.dir));
});

//  Producation Task
gulp.task(
  "default",
  gulp.series(
    gulp.parallel(
      "copy:libs",
      "scss",
      "bootstrap",
      "icons",
      "js",
      "jsPages",
      "images",
      "fonts"
    ),
    gulp.parallel("watch")
  )
);

//  Build Task
gulp.task(
  "build",
  gulp.series(
    gulp.parallel(
      "copy:libs",
      "scss",
      "bootstrap",
      "icons",
      "js",
      "jsPages",
      "images",
      "fonts"
    )
  )
);
