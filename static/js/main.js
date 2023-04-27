import * as THREE from 'three';
import {OrbitControls} from 'three/addons/controls/OrbitControls.js'
import { Rhino3dmLoader } from 'three/addons/loaders/3DMLoader.js';
import { GUI } from 'three/addons/libs/lil-gui.module.min.js';

let camera, scene, renderer;
let controls, gui;
init();
animate();

function init() {

  THREE.Object3D.DEFAULT_UP.set( 0, 0, 1 );

  renderer = new THREE.WebGLRenderer( { antialias: true } );
  renderer.setPixelRatio( window.devicePixelRatio );
  renderer.setSize( window.innerWidth, window.innerHeight );
  renderer.outputEncoding = THREE.sRGBEncoding;
  document.body.appendChild( renderer.domElement );

  camera = new THREE.PerspectiveCamera( 60, window.innerWidth / window.innerHeight, 1, 1000 );
  camera.position.set( 40, 40, 150 );

  scene = new THREE.Scene();

  const ambientLight = new THREE.AmbientLight(0xffffff, 0.2);
  scene.add(ambientLight);
  
  const directionalLight = new THREE.DirectionalLight( 0xffffff, 2 );
  directionalLight.position.set( 0, 0, 2 );
  scene.add( directionalLight );

  const loader = new Rhino3dmLoader();
  loader.setLibraryPath( 'https://cdn.jsdelivr.net/npm/rhino3dm@7.15.0/' );
  loader.load( '/static/sunlight.3dm', function ( object ) {

    scene.add( object );
    initGUI( object.userData.layers );

    // hide spinner
    document.getElementById( 'loader' ).style.display = 'none';

  } );

  controls = new OrbitControls( camera, renderer.domElement );

  window.addEventListener( 'resize', resize );
  
  const startMonthInput = document.querySelector("#start_month");
  const startDayInput = document.querySelector("#start_day");
  const startHourInput = document.querySelector("#start_hour");
  const endMonthInput = document.querySelector("#end_month");
  const endDayInput = document.querySelector("#end_day");
  const endHourInput = document.querySelector("#end_hour");

  startMonthInput.addEventListener("input", (event) => {
    const startMonth = parseInt(event.target.value);
    updateVariables(startMonth, null, null, null, null, null);
  });

  startDayInput.addEventListener("input", (event) => {
    const startDay = parseInt(event.target.value);
    updateVariables(null, startDay, null, null, null, null);
  });

  startHourInput.addEventListener("input", (event) => {
    const startHour = parseInt(event.target.value);
    updateVariables(null, null, startHour, null, null, null);
  });

  endMonthInput.addEventListener("input", (event) => {
    const endMonth = parseInt(event.target.value);
    updateVariables(null, null, null, endMonth, null, null);
  });

  endDayInput.addEventListener("input", (event) => {
    const endDay = parseInt(event.target.value);
    updateVariables(null, null, null, null, endDay, null);
  });

  endHourInput.addEventListener("input", (event) => {
    const endHour = parseInt(event.target.value);
    updateVariables(null, null, null, null, null, endHour);
  });

  function updateVariables(startMonth, startDay, startHour, endMonth, endDay, endHour) {
    const xhr = new XMLHttpRequest();
    xhr.open("POST", "/update_variables", true);
    xhr.setRequestHeader("Content-Type", "application/json;charset=UTF-8");
    xhr.onreadystatechange = function () {
      if (xhr.readyState === XMLHttpRequest.DONE) {
        if (xhr.status === 200) {
          console.log(xhr.responseText);
        } else {
          console.log("Error: " + xhr.status);
        }
      }
    };
    const data = JSON.stringify({
      startMonth: startMonth,
      startDay: startDay,
      startHour: startHour,
      endMonth: endMonth,
      endDay: endDay,
      endHour: endHour,
    });
    xhr.send(data);
  }
}

function resize() {

  const width = window.innerWidth;
  const height = window.innerHeight;

  camera.aspect = width / height;
  camera.updateProjectionMatrix();

  renderer.setSize( width, height );

}

function animate() {

  controls.update();
  renderer.render( scene, camera );

  requestAnimationFrame( animate );

}

function initGUI( layers ) {
  gui = new GUI({ 
  title: 'layers',
  });

  for ( let i = 0; i < layers.length; i ++ ) {

    const layer = layers[ i ];
    gui.add( layer, 'visible' ).name( layer.name ).onChange( function ( val ) {

      const name = this.object.name;

      scene.traverse( function ( child ) {

        if ( child.userData.hasOwnProperty( 'attributes' ) ) {

          if ( 'layerIndex' in child.userData.attributes ) {

            const layerName = layers[ child.userData.attributes.layerIndex ].name;

            if ( layerName === name ) {

              child.visible = val;
              layer.visible = val;

            }

          }

        }

      } );

    } );

  }

}